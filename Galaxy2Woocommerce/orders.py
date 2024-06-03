import requests
from woocommerce import API
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

def retrieve_order_data_from_woocommerce(wcapi):
    orders = wcapi.get("orders", params={"status": "processing"}).json()
    return orders

def post_order_data_to_erp(session_cookie, erp_endpoint, order_data):
    headers = {
        "Cookie": f"ss-id={session_cookie}",
        "Content-Type": "application/json"
    }
    json_order_data = json.dumps(order_data, ensure_ascii=False)
    response = requests.post(erp_endpoint, headers=headers, json=json.loads(json_order_data))  # Parse JSON string
    response_json = response.json()  # Parse the response JSON
    json_order_data = json.loads(json_order_data)
    doc_id = json_order_data["body"]["data"]["docid"]
    if response.status_code == 200:
        logger.info(f"Order {doc_id} posted to ERP successfully.")
    else:
        error_message = response_json["ResponseStatus"]["Message"]
        logger.error(f"Error posting order {doc_id} to ERP: {error_message}")



def get_id_from_erp(session_cookie, erp_server_ip, erp_server_port, sku):
    erp_item_url = f"http://{erp_server_ip}:{erp_server_port}/api/glx/entities/item/fetch"
    headers = {
        "Cookie": f"ss-id={session_cookie}",
        "Content-Type": "application/json"
    }
    data = {
        "SelectProperties": ["ID", "Code"],
        "Filters": [
            {
                "Name": "Code",
                "Type": "Default",
                "Operator": "Equal",
                "Value": sku
            }
        ]
    }
    response = requests.post(erp_item_url, headers=headers, json=data)
    item_data = response.json()
    
    if item_data:
        product_id = item_data[0].get("ID")
        return product_id
    else:
        return None

def construct_erp_order_data(woocommerce_order, session_cookie, erp_server_ip, erp_server_port):
    sku_list = []  # List to store skus for the current order
    for line_item in woocommerce_order["line_items"]:
        sku = line_item["sku"]
        sku_list.append(sku)  # Append the sku to the list

    erp_order_data = {
        #"header": null_var,  # Keep the fixed header
        "body": {
            "header": {
                "version": "2.3.2",
                "processtype": "B2C",
                "source": "Webshop"
            },
            "data": {
                "company": {
                    "identifier": {
                        "id": "743d7942-4ccb-474b-b140-06011f6795cc",
                        "codelist": "RCP",
                        #"idspecifier": null_var
                    },
                },
                "revisionnumber": 1,
                "doccurrency": {
                    "descr": "\u0395\u03c5\u03c1\u03ce"
                },
                "docid": woocommerce_order["id"],  # Use the order ID from WooCommerce
                "docdate": woocommerce_order["date_created"],
                "billtoaddress": {
                    "country": {
                        "descr": woocommerce_order["billing"]["country"]
                    },
                    #"municipality": null_var,
                    "prefecture": {
                        "descr": woocommerce_order["billing"]["state"]
                    },
                    "city": {
                        "descr": woocommerce_order["billing"]["city"]
                    },
                    "zipcode": woocommerce_order["billing"]["postcode"],
                    "streetname": woocommerce_order["billing"]["address_1"],
                    "streetnum": woocommerce_order["billing"]["address_2"]
                },
                "deliveryinfo": {
                    "delivdate": woocommerce_order["date_created"],
                    "address": {
                        "country": {
                            "descr": woocommerce_order["shipping"]["country"]
                        },
                        #"municipality": null_var,
                        "prefecture": {
                            "descr": woocommerce_order["shipping"]["state"]
                        },
                        "city": {
                            "descr": woocommerce_order["shipping"]["city"]
                        },
                        "zipcode": woocommerce_order["shipping"]["postcode"],
                        "streetname": woocommerce_order["shipping"]["address_1"],
                        "streetnum": woocommerce_order["shipping"]["address_2"]
                    },
                    "telephone": woocommerce_order["billing"]["phone"],
                    #"fax": null_var,
                    "email": woocommerce_order["billing"]["email"],
                    #"additionalinfo": null_var
                },
                "trader": {
                    "identifier": {
                        "id": "D3DFCC46-A35E-1198-2B52-018A024C9D07",
                        "codelist": "RCP",
                        #"idspecifier": null_var
                    },
                    #"tin": null_var,
                    "name": woocommerce_order["billing"]["first_name"]+' '+woocommerce_order["billing"]["last_name"],
                    #"mainactivity": null_var,
                    "address": {
                        "country": {
                            "descr": woocommerce_order["billing"]["country"]
                        },
                        #"municipality": null_var,
                        "prefecture": {
                            "descr": woocommerce_order["billing"]["state"]
                        },
                        "city": {
                            "descr": woocommerce_order["billing"]["city"]
                        },
                        "zipcode": woocommerce_order["billing"]["postcode"],
                        #"streetname": woocommerce_order["billing"]["address_1"],
                        "streetnum": woocommerce_order["billing"]["address_2"]
                    },
                    "telephone": woocommerce_order["billing"]["phone"],
                    #"fax": null_var,
                    "email": woocommerce_order["billing"]["email"],
                    #"website": null_var
                },
                #"comment": null_var,
                "lines": []
            },
            #"attachments": null_var
        }
    }

    # Add line items to the "lines" list in erp_order_data
    for sku in sku_list:  # Iterate through the sku list
        product_id = get_id_from_erp(session_cookie, erp_server_ip, erp_server_port, sku)
        
        if product_id:
            erp_line_item = {
                "item": {
                    "mgitemtypeid": 0,
                    "identifier": {
                        "id": product_id,
                        "idspecifier": "ID"
                    },
                },
                "qty": line_item["quantity"],
                "totalamount": line_item["total"],
                "chargestotal": 0,
            }
            erp_order_data["body"]["data"]["lines"].append(erp_line_item)
        else:
            logger.error(f"Product with Code {sku} not found in ERP.")
    
    return erp_order_data

def get_user_answers_from_db():
    answers = UserAnswer.objects.latest('id')  # Assumes a single row or latest entry contains the most recent config

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


    session_cookie = authenticate_with_erp(erp_username, erp_password, erp_server_ip, erp_server_port)
    wcapi = API(
        url=f"https://{store_domain}{store_path}",
        consumer_key=woo_consumer_key,
        consumer_secret=woo_consumer_secret,
        version="wc/v3"
    )


    if session_cookie:
        erp_endpoint = f"http://{erp_server_ip}:{erp_server_port}/services/sync/actions/postentry"

        # Get orders created after the last synced date
        orders = retrieve_order_data_from_woocommerce(wcapi)
        for order in orders:
                erp_line_items = []  # List to store all ERP line items

                for line_item in order["line_items"]:
                    sku = line_item["sku"]
                    product_id = get_id_from_erp(session_cookie, erp_server_ip, erp_server_port, sku)

                    if product_id:
                        erp_line_item = {
                            "item": {
                                "mgitemtypeid": 0,
                                "identifier": {
                                    "id": product_id,
                                    "idspecifier": "ID"
                                },
                            },
                            "qty": line_item["quantity"],
                            "totalamount": line_item["total"],
                            "chargestotal": 0,
                        }
                        erp_line_items.append(erp_line_item)
                    else:
                        logger.error(f"Product with Code {sku} not found in ERP.")

                if erp_line_items:
                    order_data = construct_erp_order_data(order, session_cookie, erp_server_ip, erp_server_port)
                    order_data["body"]["data"]["lines"] = erp_line_items
                    post_order_data_to_erp(session_cookie, erp_endpoint, order_data)