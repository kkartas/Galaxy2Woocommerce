from woocommerce import API
import requests
import base64
import ftputil, logging
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

def fetch_image_info_from_erp(session_cookie, erp_server_ip, erp_server_port):
    erp_images_path = "/services/sync/itemimages"
    erp_images_url = f"http://{erp_server_ip}:{erp_server_port}{erp_images_path}"
    headers = {
        "Cookie": f"ss-id={session_cookie}"
    }
    response = requests.get(erp_images_url, headers=headers)
    image_info = response.json()
    return image_info

def retrieve_image_from_erp(session_cookie, erp_server_ip, erp_server_port, image_id):
    erp_image_url = f"http://{erp_server_ip}:{erp_server_port}/api/glx/entities/itemimage/{image_id}"
    headers = {
        "Cookie": f"ss-id={session_cookie}"
    }
    response = requests.get(erp_image_url, headers=headers)
    image_data = response.json()["Image"]
    return image_data

def get_sku_from_erp(session_cookie, erp_server_ip, erp_server_port, item_id):
    erp_item_url = f"http://{erp_server_ip}:{erp_server_port}/api/glx/entities/item/fetch"
    headers = {
        "Cookie": f"ss-id={session_cookie}",
        "Content-Type": "application/json"
    }
    data = {
        "SelectProperties": ["ID", "Code"],
        "Filters": [
            {
                "Name": "ID",
                "Type": "Default",
                "Operator": "Equal",
                "Value": item_id
            }
        ]
    }
    response = requests.post(erp_item_url, headers=headers, json=data)
    item_data = response.json()
    
    if item_data:
        code = item_data[0].get("Code")
        return code
    else:
        return None

def upload_image_to_ftp(host, image_data, image_filename):
    with host.open(image_filename, 'wb') as ftp_file:
        ftp_file.write(image_data)


def get_woocommerce_id_by_sku(wcapi, sku):
    products = wcapi.get("products", params={"sku": sku}).json()
    if products:
        return products[0]["id"]
    else:
        return None

def image_exists_on_ftp(host, image_filename):
    if image_filename in host.listdir(host.curdir):
        print(f"Image '{image_filename}' already exists on FTP.")
        return True
    else:
        print(f"Image '{image_filename}' does not exist on FTP.")
        return False



def set_product_image_in_woocommerce(wcapi, product_id, image_url):
    image_data = {
        "images": [
            {
            "src": image_url
            }
        ]
    }
    response = wcapi.put(f'products/{product_id}', image_data)

    if response.status_code == 201:
        logger.info(f"Image set as product image for product ID '{product_id}'")
    else:
        logger.error(f"Error setting image as product image for product ID '{product_id}': {response.json()}")

def get_user_answers_from_db():
    answers = UserAnswer.objects.latest('id')

    return answers

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
    ftp_server = user_answers.ftp_server
    ftp_username = user_answers.ftp_username
    ftp_password = user_answers.ftp_password
    ftp_folder = user_answers.ftp_folder

    session_cookie = authenticate_with_erp(erp_username, erp_password, erp_server_ip, erp_server_port)
    wcapi = API(
        url=f"https://{store_domain}{store_path}",
        consumer_key=woo_consumer_key,
        consumer_secret=woo_consumer_secret,
        version="wc/v3"
    )

    if session_cookie:
        erp_images = fetch_image_info_from_erp(session_cookie, erp_server_ip, erp_server_port)

        if erp_images:
        # Establish FTP connection
            with ftputil.FTPHost(ftp_server, ftp_username, ftp_password) as host:
                host.chdir(ftp_folder)
        
                erp_images = fetch_image_info_from_erp(session_cookie, erp_server_ip, erp_server_port)
                if not erp_images:
                    logger.error("No images retrieved from ERP.")
                    return

                for image_info in erp_images:
                    item_id = image_info["ItemID"]
                    sku = get_sku_from_erp(session_cookie, erp_server_ip, erp_server_port, item_id)
            
                    if sku:
                         woocommerce_id = get_woocommerce_id_by_sku(wcapi, sku)
                         if woocommerce_id is not None:
                            image_data = retrieve_image_from_erp(session_cookie, erp_server_ip, erp_server_port, image_info["ID"])
                            image_filename = f"{sku}.png"

                            if not image_exists_on_ftp(host, image_filename):
                                image_data_bytes = base64.b64decode(image_data)
                                upload_image_to_ftp(host, image_data_bytes, image_filename)
                                image_url = f"https://{ftp_server}{ftp_folder}/{image_filename}"
                                set_product_image_in_woocommerce(wcapi, woocommerce_id, image_url)
                                logger.info(f"Image set for SKU '{sku}' in WooCommerce.")
                            else:
                                logger.info(f"Image '{image_filename}' already exists on FTP. Skipping upload and WooCommerce update.")
                         else:
                            logger.error(f"SKU '{sku}' not found in WooCommerce.")

        else:
            logger.error("No images retrieved from ERP.")
    else:
        logger.error("Authentication with ERP failed.")
