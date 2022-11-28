"""The location information microservices. Manages all user location information 
stored in the database

Actions
-------
get - get an existing user's location information
update - update an existing user's location information
add - adds a new user's location information
delete - delete's an existing user's location information

Location Data Object
--------------------
username: str - username of user (UNIQUE)
latitude: float - latitude of coordinates
longitude: float - longitude of coordinates"""

import os
import json
import logging
from typing import Dict, Any

import azure.functions as func
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from dotenv import load_dotenv
load_dotenv()


ENDPOINT = os.environ.get("COSMOS_ENDPOINT") or ""
KEY = os.environ.get("COSMOS_KEY") or ""
DATABASE_NAME = os.environ.get("DATABASE_NAME") or ""
CONTAINER_NAME = os.environ.get("CONTAINER_NAME") or ""


client = CosmosClient(ENDPOINT, credential=KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)


def get_location_object(username: str) -> Dict[str,Any]:
    return list(container.query_items(f"SELECT * FROM Container AS C WHERE C.id = 'location_{username}'", enable_cross_partition_query=True))[0]

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('locationinfo lambda triggered')

    req_type = req.params.get('type')

    if req_type == 'get':
        logging.info('    get request received')
        username = req.params.get('username')
        if username is None:
            logging.error('        request malformed: username missing')
            return func.HttpResponse('Request malformed: username missing', status_code=400)
        try:
            location_object = get_location_object(username)
        except CosmosHttpResponseError as e:
            logging.warn('        user does not exist')
            logging.warn(e.exc_msg)
            return func.HttpResponse('User does not exist', status_code=400)
        else:
            res_object = {'latitude': location_object['latitude'], 'longitude': location_object['logitude']}
            logging.info('        request successful')
            return func.HttpResponse(json.dumps(res_object), status_code=200)

    elif req_type == 'update':
        logging.info('    update request received')
        username = req.params.get('username')
        if username is None:
            logging.error('        request malformed: username missing')
            return func.HttpResponse('Request malformed: username missing', status_code=400)
        try:
            location_object = location_object = get_location_object(username)
            body: dict[str,str] = req.get_json()
            location_object['latitude'] = body['latitude']
            location_object['logitude'] = body['logitude']
            container.upsert_item(location_object)
        except ValueError:
            logging.error('        request malformed: body malformed')
            return func.HttpResponse('Request malformed: body malformed', status_code=400)
        except CosmosHttpResponseError as e:
            logging.warn('        user does not exist')
            logging.warn(e.exc_msg)
            return func.HttpResponse('User does not exist', status_code=400)
        else:
            logging.info('        request successful')
            return func.HttpResponse('Okay', status_code=200)

    elif req_type == 'add':
        logging.info('    add request received')
        try:
            username = req.params.get('username')
            if username is None:
                return func.HttpResponse('Request malformed: username missing', status_code=400)
            body: dict[str,str] = req.get_json()
            location_object = {'id': f'locations_{username}', 'latitude': body['latitude'], 'longitude': body['latitude']}
            container.upsert_item(location_object)
        except ValueError:
            logging.error('        request malformed: body malformed')
            return func.HttpResponse('Request malformed: body malformed', status_code=400)
        except CosmosHttpResponseError as e:
            logging.warn('        user location already exists')
            logging.warn(e.exc_msg)
            return func.HttpResponse('User location already exists', status_code=400)
        else:
            logging.info('        request successful')
            return func.HttpResponse('Okay', status_code=200)
        
    elif req_type == 'delete':
        logging.info('    delete request received')
        username = req.params.get('username')
        if username is None:
            logging.error('        request malformed: username missing')
            return func.HttpResponse('Request malformed: username missing', status_code=400)
        try:
            container.delete_item(item=f'locations_{username}', partition_key=f'locations_{username}')
        except CosmosHttpResponseError as e:
            logging.warn('        user does not exist')
            logging.warn(e.exc_msg)
            return func.HttpResponse('User does not exist', status_code=400)
        else:
            logging.info('        request successful')
            return func.HttpResponse('Okay', status_code=200)
    
    else:
        logging.error('    unknown request received')
        return func.HttpResponse('Request malformed: unknown request type', status_code=400)
