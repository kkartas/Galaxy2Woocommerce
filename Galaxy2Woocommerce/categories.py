from woocommerce import API
import requests
import json, logging
from .models import CategoryMapping, UserAnswer

logger = logging.getLogger(__name__)

def authenticate_with_erp(erp_username, erp_password, erp_server_ip, erp_server_port):
    erp_auth_path = "/auth"
    erp_auth_url = f"http://{erp_server_ip}:{erp_server_port}{erp_auth_path}"
    erp_auth_data = {
        "username": erp_username,
        "password": erp_password
    }
    response = requests.get(erp_auth_url, params=erp_auth_data)

    session_cookie = response.cookies.get("ss-id")
    return session_cookie


def fetch_categories_from_erp(session_cookie, erp_server_ip, erp_server_port):
    erp_categories_path = "/services/sync/itemcategories"
    erp_categories_url = f"http://{erp_server_ip}:{erp_server_port}{erp_categories_path}"
    headers = {
        "Cookie": f"ss-id={session_cookie}"
    }
    response = requests.get(erp_categories_url, headers=headers)
    categories = response.json()
    return categories


def transform_category_for_woocommerce(category, categories_mapping):
    transformed_category = {
        "name": category["Description"],
        "slug": category["Code"],
        "parent": categories_mapping.get(category["ParentNodeID"]),
        "erp_id": category["ID"],
        "woocommerce_id": None  # Initialize WooCommerce ID as None
    }

    return transformed_category

def read_categories_mapping():
    mappings = CategoryMapping.objects.all()
    categories_mapping = {mapping.erp_id: mapping.woocommerce_id for mapping in mappings}
    return categories_mapping

def get_user_answers_from_db():
    answers = UserAnswer.objects.latest('id')
    return(answers)

def run_import(user_answers):

    user_answers = get_user_answers_from_db()

    store_domain = user_answers.store_domain
    store_path = user_answers.store_path
    erp_server_ip = user_answers.erp_server_ip
    erp_server_port = user_answers.erp_server_port
    erp_username = user_answers.erp_username
    erp_password = user_answers.erp_password
    woo_consumer_key = user_answers.woo_consumer_key
    woo_consumer_secret = user_answers.woo_consumer_secret

    session_cookie = authenticate_with_erp(erp_username, erp_password, erp_server_ip, erp_server_port)
    wcapi = API(
        url=f"https://{store_domain}{store_path}",
        consumer_key=woo_consumer_key,
        consumer_secret=woo_consumer_secret,
        version="wc/v3"
    )

    categories_mapping = read_categories_mapping()  # Load categories mapping from file

    if session_cookie:
        erp_categories = fetch_categories_from_erp(session_cookie, erp_server_ip, erp_server_port)

        if erp_categories:
            for category in erp_categories:
                transformed_category = transform_category_for_woocommerce(category, categories_mapping)

                if transformed_category["woocommerce_id"]:
                    logger.info(f"Category '{transformed_category['name']}' already exists in WooCommerce.")
                else:
                # Use the WooCommerce API to check if the category exists
                    existing_categories = wcapi.get("products/categories", params={"slug": transformed_category["slug"]}).json()

                    if existing_categories and isinstance(existing_categories, list) and len(existing_categories) > 0:
                        transformed_category["woocommerce_id"] = existing_categories[0]["id"]
                        categories_mapping[category["ID"]] = existing_categories[0]["id"]
                        logger.info(f"Category '{transformed_category['name']}' already exists in WooCommerce.")
                    else:
                    # Use the WooCommerce API to create a category
                        created_category = wcapi.post("products/categories", transformed_category).json()

                        if "message" in created_category:
                            logger.error(f"Error posting category {transformed_category['name']}: {created_category['message']}")
                        else:
                            logger.info(f"Category {transformed_category['name']} successfully posted to WooCommerce.")

                        if "id" in created_category:
                            categories_mapping[category["ID"]] = created_category["id"]

        # Save the updated categories_mapping to a JSON file
            for erp_id, woocommerce_id in categories_mapping.items():
                 mapping, created = CategoryMapping.objects.get_or_create(erp_id=erp_id)
                 mapping.woocommerce_id = woocommerce_id
                 mapping.save()

        else:
            logger.error("No categories retrieved from ERP.")
        logger.info("Categories synchronization completed.")
    else:
        logger.error("Authentication with ERP failed.")

