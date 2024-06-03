from woocommerce import API
import requests
import json, logging
from .models import UserAnswer

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

def fetch_item_balances_from_erp(session_cookie, erp_server_ip, erp_server_port):
    erp_balances_path = "/services/sync/itembalances"
    erp_balances_url = f"http://{erp_server_ip}:{erp_server_port}{erp_balances_path}"
    headers = {
        "Cookie": f"ss-id={session_cookie}"
    }
    response = requests.get(erp_balances_url, headers=headers)
    item_balances = response.json()
    return item_balances

def transform_balance_for_woocommerce(balance):
    transformed_balance = {
        "manage_stock": True,  # Enable stock management for the product
        "stock_quantity": balance["Balance"],
    }
    return transformed_balance

def get_product_id_by_sku(wcapi, sku):
    # Use the WooCommerce API to retrieve the product by SKU
    response = wcapi.get("products", params={"sku": sku})
    products = response.json()
    
    if products and isinstance(products, list) and len(products) > 0:
        return products[0]["id"]
    else:
        return None

def get_user_answers_from_db():
    answers = UserAnswer.objects.latest('id')
    return(answers)

def run_import():

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

    if session_cookie:
        erp_balances = fetch_item_balances_from_erp(session_cookie, erp_server_ip, erp_server_port)

        if erp_balances:
            for balance in erp_balances:
                sku = balance["Code"]
                transformed_balance = transform_balance_for_woocommerce(balance)

                # Get the product ID using the SKU
                product_id = get_product_id_by_sku(wcapi, sku)

                if product_id:
                    # Use the WooCommerce API to update the product by ID
                    updated_product = wcapi.put(f"products/{product_id}", transformed_balance).json()

                    if "message" in updated_product:
                        logger.error(f"Error updating item balance for SKU '{sku}': {updated_product['message']}")
                    else:
                        logger.info(f"Item balance for SKU '{sku}' successfully updated.")
                else:
                    logger.error(f"Product with SKU '{sku}' not found in WooCommerce.")

        else:
            logger.error("No item balances retrieved from ERP.")
        logger.info("Balance synchronization completed.")
    else:
        logger.error("Authentication with ERP failed.")
