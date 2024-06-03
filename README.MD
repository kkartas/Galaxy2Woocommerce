
# Galaxy2Woocommerce

## Overview

**Galaxy2Woocommerce** is a Python-based application designed to integrate the Epsilon Singularlogic Galaxy ERP with WooCommerce. This tool enables seamless data transfer and synchronization between Epsilon Singularlogic Galaxy ERP and WooCommerce, facilitating efficient e-commerce operations.

## Features
- **Data Synchronization**: Automatically sync data between Epsilon Singularlogic Galaxy ERP and WooCommerce.
- **API Integration**: Utilizes Epsilon Singularlogic Galaxy ERP and WooCommerce APIs for seamless integration.
- **Error Handling**: Robust error handling to ensure data integrity.

## Prerequisites
- Python 3.8+
- Epsilon Singularlogic Galaxy ERP API credentials
- WooCommerce API credentials

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/kkartas/Galaxy2Woocommerce.git
   cd Galaxy2Woocommerce
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv env
   source env/bin/activate   # On Windows: env\ScriptS\Activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **API Credentials**
   - Create a `config.json` file in the root directory with your API credentials:
     ```json
     {
       "galaxy_api_key": "your_galaxy_api_key",
       "woocommerce_consumer_key": "your_woocommerce_consumer_key",
       "woocommerce_consumer_secret": "your_woocommerce_consumer_secret",
       "woocommerce_url": "your_woocommerce_store_url"
     }
     ```

## Usage

1. **Run the Application**
   ```bash
   python manage.py runserver
   ```

2. **Access the Application**
   - Open your browser and navigate to `http://127.0.0.1:8000`.

3. **Synchronization**
   - The application will start synchronizing data between Epsilon Singularlogic Galaxy ERP and WooCommerce based on the predefined schedule or triggers.

## Directory Structure

- **Galaxy2Woocommerce**: Main application directory.
- **manage.py**: Entry point for the Django application.
- **requirements.txt**: Python dependencies.

## Acknowledgments

WooCommerce and Epsilon Singularlogic Galaxy ERP are not my property or trademarks. Special thanks to the contributors and the open-source community for their invaluable support.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
