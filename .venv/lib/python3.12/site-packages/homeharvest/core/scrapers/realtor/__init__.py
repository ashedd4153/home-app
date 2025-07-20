"""
homeharvest.realtor.__init__
~~~~~~~~~~~~

This module implements the scraper for realtor.com
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from json import JSONDecodeError
from typing import Dict, Union

from tenacity import (
    retry,
    retry_if_exception_type,
    wait_exponential,
    stop_after_attempt,
)

from .. import Scraper
from ..models import (
    Property,
    ListingType,
    ReturnType
)
from .queries import GENERAL_RESULTS_QUERY, SEARCH_HOMES_DATA, HOMES_DATA, HOME_FRAGMENT
from .processors import (
    process_property,
    process_extra_property_details,
    get_key
)


class RealtorScraper(Scraper):
    SEARCH_GQL_URL = "https://www.realtor.com/api/v1/rdc_search_srp?client_id=rdc-search-new-communities&schema=vesta"
    PROPERTY_URL = "https://www.realtor.com/realestateandhomes-detail/"
    PROPERTY_GQL = "https://graph.realtor.com/graphql"
    ADDRESS_AUTOCOMPLETE_URL = "https://parser-external.geo.moveaws.com/suggest"
    NUM_PROPERTY_WORKERS = 20
    DEFAULT_PAGE_SIZE = 200

    def __init__(self, scraper_input):
        super().__init__(scraper_input)

    def handle_location(self):
        params = {
            "input": self.location,
            "client_id": self.listing_type.value.lower().replace("_", "-"),
            "limit": "1",
            "area_types": "city,state,county,postal_code,address,street,neighborhood,school,school_district,university,park",
        }

        response = self.session.get(
            self.ADDRESS_AUTOCOMPLETE_URL,
            params=params,
        )
        response_json = response.json()

        result = response_json["autocomplete"]

        if not result:
            return None

        return result[0]

    def get_latest_listing_id(self, property_id: str) -> str | None:
        query = """query Property($property_id: ID!) {
                    property(id: $property_id) {
                        listings {
                            listing_id
                            primary
                        }
                    }
                }
                """

        variables = {"property_id": property_id}
        payload = {
            "query": query,
            "variables": variables,
        }

        response = self.session.post(self.SEARCH_GQL_URL, json=payload)
        response_json = response.json()

        property_info = response_json["data"]["property"]
        if property_info["listings"] is None:
            return None

        primary_listing = next(
            (listing for listing in property_info["listings"] if listing["primary"]),
            None,
        )
        if primary_listing:
            return primary_listing["listing_id"]
        else:
            return property_info["listings"][0]["listing_id"]

    def handle_home(self, property_id: str) -> list[Property]:
        query = (
            """query Home($property_id: ID!) {
                    home(property_id: $property_id) %s
                }"""
            % HOMES_DATA
        )

        variables = {"property_id": property_id}
        payload = {
            "query": query,
            "variables": variables,
        }

        response = self.session.post(self.SEARCH_GQL_URL, json=payload)
        response_json = response.json()

        property_info = response_json["data"]["home"]

        if self.return_type != ReturnType.raw:
            return [process_property(property_info, self.mls_only, self.extra_property_data, 
                                   self.exclude_pending, self.listing_type, get_key, process_extra_property_details)]
        else:
            return [property_info]



    def general_search(self, variables: dict, search_type: str) -> Dict[str, Union[int, Union[list[Property], list[dict]]]]:
        """
        Handles a location area & returns a list of properties
        """

        date_param = ""
        if self.listing_type == ListingType.SOLD:
            if self.date_from and self.date_to:
                date_param = f'sold_date: {{ min: "{self.date_from}", max: "{self.date_to}" }}'
            elif self.last_x_days:
                date_param = f'sold_date: {{ min: "$today-{self.last_x_days}D" }}'
        else:
            if self.date_from and self.date_to:
                date_param = f'list_date: {{ min: "{self.date_from}", max: "{self.date_to}" }}'
            elif self.last_x_days:
                date_param = f'list_date: {{ min: "$today-{self.last_x_days}D" }}'

        property_type_param = ""
        if self.property_type:
            property_types = [pt.value for pt in self.property_type]
            property_type_param = f"type: {json.dumps(property_types)}"

        sort_param = (
            "sort: [{ field: sold_date, direction: desc }]"
            if self.listing_type == ListingType.SOLD
            else ""  #: "sort: [{ field: list_date, direction: desc }]"  #: prioritize normal fractal sort from realtor
        )

        pending_or_contingent_param = (
            "or_filters: { contingent: true, pending: true }" if self.listing_type == ListingType.PENDING else ""
        )

        listing_type = ListingType.FOR_SALE if self.listing_type == ListingType.PENDING else self.listing_type
        is_foreclosure = ""

        if variables.get("foreclosure") is True:
            is_foreclosure = "foreclosure: true"
        elif variables.get("foreclosure") is False:
            is_foreclosure = "foreclosure: false"

        if search_type == "comps":  #: comps search, came from an address
            query = """query Property_search(
                    $coordinates: [Float]!
                    $radius: String!
                    $offset: Int!,
                    ) {
                        home_search(
                            query: {
                                %s
                                nearby: {
                                    coordinates: $coordinates
                                    radius: $radius
                                }
                                status: %s
                                %s
                                %s
                                %s
                            }
                            %s
                            limit: 200
                            offset: $offset
                    ) %s
                }""" % (
                is_foreclosure,
                listing_type.value.lower(),
                date_param,
                property_type_param,
                pending_or_contingent_param,
                sort_param,
                GENERAL_RESULTS_QUERY,
            )
        elif search_type == "area":  #: general search, came from a general location
            query = """query Home_search(
                                $city: String,
                                $county: [String],
                                $state_code: String,
                                $postal_code: String
                                $offset: Int,
                            ) {
                                home_search(
                                    query: {
                                        %s
                                        city: $city
                                        county: $county
                                        postal_code: $postal_code
                                        state_code: $state_code
                                        status: %s
                                        %s
                                        %s
                                        %s
                                    }
                                    bucket: { sort: "fractal_v1.1.3_fr" }
                                    %s
                                    limit: 200
                                    offset: $offset
                                ) %s
                            }""" % (
                is_foreclosure,
                listing_type.value.lower(),
                date_param,
                property_type_param,
                pending_or_contingent_param,
                sort_param,
                GENERAL_RESULTS_QUERY,
            )
        else:  #: general search, came from an address
            query = (
                """query Property_search(
                        $property_id: [ID]!
                        $offset: Int!,
                    ) {
                        home_search(
                            query: {
                                property_id: $property_id
                            }
                            limit: 1
                            offset: $offset
                        ) %s
                    }"""
                % GENERAL_RESULTS_QUERY
            )

        payload = {
            "query": query,
            "variables": variables,
        }

        response = self.session.post(self.SEARCH_GQL_URL, json=payload)
        response_json = response.json()
        search_key = "home_search" if "home_search" in query else "property_search"

        properties: list[Union[Property, dict]] = []

        if (
            response_json is None
            or "data" not in response_json
            or response_json["data"] is None
            or search_key not in response_json["data"]
            or response_json["data"][search_key] is None
            or "results" not in response_json["data"][search_key]
        ):
            return {"total": 0, "properties": []}

        properties_list = response_json["data"][search_key]["results"]
        total_properties = response_json["data"][search_key]["total"]
        offset = variables.get("offset", 0)

        #: limit the number of properties to be processed
        #: example, if your offset is 200, and your limit is 250, return 50
        properties_list: list[dict] = properties_list[: self.limit - offset]

        if self.extra_property_data:
            property_ids = [data["property_id"] for data in properties_list]
            extra_property_details = self.get_bulk_prop_details(property_ids) or {}

            for result in properties_list:
                specific_details_for_property = extra_property_details.get(result["property_id"], {})

                #: address is retrieved on both homes and search homes, so when merged, homes overrides,
                # this gets the internal data we want and only updates that (migrate to a func if more fields)
                if "location" in specific_details_for_property:
                    result["location"].update(specific_details_for_property["location"])
                    del specific_details_for_property["location"]

                result.update(specific_details_for_property)

        if self.return_type != ReturnType.raw:
            with ThreadPoolExecutor(max_workers=self.NUM_PROPERTY_WORKERS) as executor:
                futures = [executor.submit(process_property, result, self.mls_only, self.extra_property_data, 
                                         self.exclude_pending, self.listing_type, get_key, process_extra_property_details) for result in properties_list]

                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        properties.append(result)
        else:
            properties = properties_list

        return {
            "total": total_properties,
            "properties": properties,
        }

    def search(self):
        location_info = self.handle_location()
        if not location_info:
            return []

        location_type = location_info["area_type"]

        search_variables = {
            "offset": 0,
        }

        search_type = (
            "comps"
            if self.radius and location_type == "address"
            else "address" if location_type == "address" and not self.radius else "area"
        )
        if location_type == "address":
            if not self.radius:  #: single address search, non comps
                property_id = location_info["mpr_id"]
                return self.handle_home(property_id)

            else:  #: general search, comps (radius)
                if not location_info.get("centroid"):
                    return []

                coordinates = list(location_info["centroid"].values())
                search_variables |= {
                    "coordinates": coordinates,
                    "radius": "{}mi".format(self.radius),
                }

        elif location_type == "postal_code":
            search_variables |= {
                "postal_code": location_info.get("postal_code"),
            }

        else:  #: general search, location
            search_variables |= {
                "city": location_info.get("city"),
                "county": location_info.get("county"),
                "state_code": location_info.get("state_code"),
                "postal_code": location_info.get("postal_code"),

            }

        if self.foreclosure:
            search_variables["foreclosure"] = self.foreclosure

        result = self.general_search(search_variables, search_type=search_type)
        total = result["total"]
        homes = result["properties"]

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.general_search,
                    variables=search_variables | {"offset": i},
                    search_type=search_type,
                )
                for i in range(
                    self.DEFAULT_PAGE_SIZE,
                    min(total, self.limit),
                    self.DEFAULT_PAGE_SIZE,
                )
            ]

            for future in as_completed(futures):
                homes.extend(future.result()["properties"])

        return homes



    @retry(
        retry=retry_if_exception_type(JSONDecodeError),
        wait=wait_exponential(min=4, max=10),
        stop=stop_after_attempt(3),
    )
    def get_bulk_prop_details(self, property_ids: list[str]) -> dict:
        """
        Fetch extra property details for multiple properties in a single GraphQL query.
        Returns a map of property_id to its details.
        """
        if not self.extra_property_data or not property_ids:
            return {}

        property_ids = list(set(property_ids))

        # Construct the bulk query
        fragments = "\n".join(
            f'home_{property_id}: home(property_id: {property_id}) {{ ...HomeData }}'
            for property_id in property_ids
        )
        query = f"""{HOME_FRAGMENT}
        
        query GetHomes {{
            {fragments}
        }}"""

        response = self.session.post(self.SEARCH_GQL_URL, json={"query": query})
        data = response.json()

        if "data" not in data:
            return {}

        properties = data["data"]
        return {data.replace('home_', ''): properties[data] for data in properties if properties[data]}


