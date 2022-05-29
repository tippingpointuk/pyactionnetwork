#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from urllib.parse import quote
from ratelimit import limits, RateLimitException
from backoff import on_exception, expo


class ActionNetworkApi:
    """Python wrapper for Action Network API."""

    def __init__(self, api_key, **kwargs):
        """Instantiate the API client and get config."""
        self.headers = {"OSDI-API-Token": api_key}
        self.refresh_config()
        self.base_url = self.config.get('links', {}).get('self', 'https://actionnetwork.org/api/v2/')
        print(self.config['motd'])

    def refresh_config(self):
        """Get a new version of the base_url config."""
        self.config = requests.get(url="https://actionnetwork.org/api/v2/",
                                   headers=self.headers).json()

    def resource_to_url(self, resource):
        """Convert a named endpoint into a URL.

        Args:
            resource (str):
                resource name (e.g. 'links', 'people', etc.)
        Returns:
            (str) Full resource endpoint URL.
        """
        if resource in self.config.get('_links', {}).keys():
            return self.config['_links'][resource]['href']
        try:
            return self.config['_links']["osdi:{0}".format(resource)]['href']
        except KeyError:
            raise KeyError("Unknown Resource %s", resource)

    # Action Network has a 4 per second rate limit, see
    # https://actionnetwork.org/docs/#considerations
    @on_exception(expo, RateLimitException, max_tries=8)
    @limits(calls=4, period=1)
    def client(self, method, url, params=None, json=None):
        return requests.request(method, url, headers=self.headers, params=params, json=json).json()

    def get_resource(self, resource, params={}):
        """Get a resource endpoint by name.

        Args:
            resource (str):
                Resource endpoint of the format 'people', 'events', 'lists', etc.
        Returns:
            (dict) API response from endpoint or `None` if not found/valid.
        """
        url = self.resource_to_url(resource)
        return self.client('GET', url, params=params)

    def get_resource_list(self, resource=None, url=None, filter=None, resources=None):
        if not resources:
            resources = []

        if resource and not url:
            url_no_filter = self.resource_to_url(resource)
            if filter:
                url = f"{url_no_filter}?filter={quote(filter)}"
            else:
                url = url_no_filter

        data = self.client('GET', url)
        if data.get('error', None):
            print(data['error'])
            data = self.client('GET', url_no_filter)

        resources += [d for d in data['_embedded'][f'osdi:{resource}']]

        if data.get('_links', {}).get('next', None):
            next_url = data.get('_links').get('next').get('href')
            return self.get_resource_list(url=next_url, resource=resource, resources=resources)
        return resources

    def get_person(self, person_id=None, search_by='email', search_string=None):
        """Search for a user.

        Args:
            search_by (str):
                Field by which to search for a user. 'email' is the default.
            search_string (str):
                String to search for within the field given by `search_by`

        Returns:
            (dict) person json if found, otherwise `None`
        """
        if person_id:
            url = "{0}people/{1}".format(self.base_url, person_id)
        else:
            url = "{0}people/?filter={1} eq '{2}'".format(
                self.base_url,
                search_by,
                quote(search_string))

        person = self.client('GET', url)
        return person

    def create_person(self,
                      email=None,
                      given_name='',
                      family_name='',
                      address=list(),
                      city='',
                      state='',
                      country='',
                      postal_code='',
                      tags=list(),
                      custom_fields=dict()):
        """Create a user.

        Documentation here: https://actionnetwork.org/docs/v2/person_signup_helper

        Args:
            email ((str, list)):
                email address (or, if list, addresses) of the person
            given_name (str, optional):
                first name of the person
            family_name (str, optional):
                last name of the person
            address ((str, list), optional):
                address of the person. if a str, then one address line
                only. if a list, then address_lines in action network
                will be respected (for apartments or companies etc.)
            city (str, optional):
                city of the person.
            country (str, optional):
                country code for the person.
            postal_code (str, optional):
                postal or zip code of the person.
            tags ((str, list), optional):
                add any tags you want when creating a person.
            custom_fields (dict, optional):
                dict of custom fields to pass to the api
        Returns:
            (dict) A fully fleshed out dictionary representing a person,
            containing the above attributes and additional attributes
            set by Action Network.
        """
        url = "{0}people/".format(self.base_url)
        payload = {
            'person': {
                'family_name': family_name,
                'given_name': given_name,
                'postal_addresses': [{
                    'address_lines': list(address),
                    'locality': city,
                    'region': state,
                    'country': country,
                    'postal_code': postal_code
                }],
                'email_addresses': [{
                    'address': email
                }],
                'custom_fields': custom_fields,
            },
            'add_tags': list(tags)
        }

        resp = self.client('POST', url, json=payload)
        return resp

    def update_person(self,
                      person_id=None,
                      email=None,
                      given_name=None,
                      family_name=None,
                      address=list(),
                      city=None,
                      state=None,
                      country=None,
                      postal_code=None,
                      tags=list(),
                      custom_fields=dict()):
        """Update a user.

        Args:
            email ((str, list)):
                email address (or, if list, addresses) of the person
            given_name (str, optional):
                first name of the person
            family_name (str, optional):
                last name of the person
            address ((str, list), optional):
                address of the person. if a str, then one address line
                only. if a list, then address_lines in action network
                will be respected (for apartments or companies etc.)
            city (str, optional):
                city of the person.
            country (str, optional):
                country code for the person.
            postal_code (str, optional):
                postal or zip code of the person.
            tags ((str, list), optional):
                add any tags you want when creating a person.
            custom_fields (dict, optional):
                dict of custom fields to pass to the api
        Returns:
            (dict) A fully fleshed out dictionary representing a person, containing the above
            attributes and additional attributes set by Action Network.
        """
        url = "{0}people/{1}".format(self.base_url, person_id)
        payload = {
            'family_name': family_name,
            'given_name': given_name,
            'postal_addresses': [{
                'address_lines': list(address),
                'locality': city,
                'region': state,
                'country': country,
                'postal_code': postal_code
            }],
            'email_addresses': [{
                'address': email
            }],
            'add_tags': list(tags),
            'custom_fields': custom_fields,
        }

        resp = self.client('PUT', url, json=payload)
        return resp.json()

    def search(self, resource, operator, term):
        """Search for a given `term` within a `resource`.

        Args:
            resource (str):
                Resource family within which to search. Should be one of
                'people', 'events', etc.
            operator (str):
                Operator by which to search. Should be something like
                'eq', 'gt', 'lt', etc.
            term (str):
                Term for which to search. Can be an email, name, etc.

        Returns:
            (dict) Object if found, otherwise `None`.
        """
        pass
