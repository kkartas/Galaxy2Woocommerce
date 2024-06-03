from woocommerce import API
import requests
import json
import logging
from django.http import JsonResponse
from .models import CategoryMapping
from .models import UserAnswer

# Setting up logging
logger = logging.getLogger(__name__)


def authenticate_with_erp(erp_username, erp_password, erp_server_ip, erp_server_port):
    erp_auth_path = "/auth"
    erp_auth_url = f"http://{erp_server_ip}:{erp_server_port}{erp_auth_path}"
    erp_auth_data = {
        "username": erp_username,
        "password": erp_password
    }

    try:
        response = requests.get(erp_auth_url, params=erp_auth_data)
        response.raise_for_status()
        session_cookie = response.cookies.get("ss-id")
        return session_cookie
    except Exception as e:
        logger.error(f"Error during ERP authentication: {e}")
        return None

def fetch_items_from_erp(session_cookie, erp_server_ip, erp_server_port, last_revision_number):
    erp_items_path = "/services/sync/items"
    erp_items_url = f"http://{erp_server_ip}:{erp_server_port}{erp_items_path}"
    params = {
        "RevisionNumber": last_revision_number
    }
    headers = {
        "Cookie": f"ss-id={session_cookie}"
    }

    try:
        response = requests.get(erp_items_url, headers=headers, params=params)
        response.raise_for_status()
        items = response.json()
        return items
    except Exception as e:
        logger.error(f"Error fetching items from ERP: {e}")
        return []

def read_categories_mapping():
    mappings = CategoryMapping.objects.all()
    categories_mapping = {mapping.erp_id: mapping.woocommerce_id for mapping in mappings}
    return categories_mapping


def transform_item_for_woocommerce(item, categories_mapping):
    erp_categories = item.get("ItemCategories", [])
    erp_child_category = erp_categories[-1] if erp_categories else None
    woocommerce_category_id = categories_mapping.get(erp_child_category["CategoryLeafID"]) if erp_child_category else None

    transformed_item = {
        "weight": str(item["Weight"]),
        "regular_price": str(item["ItemPrice"]),
        "name": item["Description"],
        "description": item["ExtDescription"],
        "sku": item["Code"],
        "meta_data": [
            {
                "key": "revision_number",
                "value": str(item["RevisionNumber"])
            }
        ],
        "categories": [{"id": woocommerce_category_id}] if woocommerce_category_id is not None else []
    }

    return transformed_item

def get_user_answers_from_db():
    answers = UserAnswer.objects.latest('id')  # Assumes a single row or latest entry contains the most recent config

    return answers

def instance_to_dict(instance):
    return {field.name: getattr(instance, field.name) for field in instance._meta.fields}


def run_import():

    user_answer_instance = get_user_answers_from_db()
    user_answers = instance_to_dict(user_answer_instance)

    response_data = []

    store_domain = user_answers["store_domain"]
    store_path = user_answers["store_path"]
    erp_server_ip = user_answers["erp_server_ip"]
    erp_server_port = user_answers["erp_server_port"]
    erp_username = user_answers["erp_username"]
    erp_password = user_answers["erp_password"]
    woo_consumer_key = user_answers["woo_consumer_key"]
    woo_consumer_secret = user_answers["woo_consumer_secret"]
    last_revision_number = user_answers["last_revision_number"]

    session_cookie = authenticate_with_erp(erp_username, erp_password, erp_server_ip, erp_server_port)

    wcapi = API(
        url=f"https://{store_domain}{store_path}",
        consumer_key=woo_consumer_key,
        consumer_secret=woo_consumer_secret,
        version="wc/v3"
    )

    if session_cookie:
        erp_items = fetch_items_from_erp(session_cookie, erp_server_ip, erp_server_port, last_revision_number)
        if erp_items:
            categories_mapping = read_categories_mapping()
            for item in erp_items:
                transformed_item = transform_item_for_woocommerce(item, categories_mapping)
                existing_product = wcapi.get("products", params={"sku": transformed_item["sku"]}).json()

                if existing_product:
                    product_id = existing_product[0]["id"]
                    updated_product = wcapi.put(f"products/{product_id}", transformed_item).json()

                    if "message" in updated_product:
                        logger.error(f"Error updating item {transformed_item['name']}: {updated_product['message']}")
                    else:
                        logger.info(f"Item {transformed_item['name']} successfully updated in WooCommerce.")
                else:
                    created_item = wcapi.post("products", transformed_item).json()

                    if "message" in created_item:
                        logger.error(f"Error posting item {transformed_item['name']}: {created_item['message']}")
                    else:
                        logger.info(f"Item {transformed_item['name']} successfully posted to WooCommerce.")
                user_answers["last_revision_number"] = item["RevisionNumber"]
                user_answer_instance.last_revision_number = user_answers["last_revision_number"]
                user_answer_instance.save()
        else:
            logger.info("All items has been synced!")      
            
    return JsonResponse({"messages": response_data})

