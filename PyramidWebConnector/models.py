from django.db import models

class UserAnswer(models.Model):
    store_domain = models.CharField(max_length=255)
    store_path = models.CharField(max_length=255)
    erp_server_ip = models.CharField(max_length=255)
    erp_server_port = models.CharField(max_length=255)
    erp_username = models.CharField(max_length=255)
    erp_password = models.CharField(max_length=255)
    woo_consumer_key = models.CharField(max_length=255)
    woo_consumer_secret = models.CharField(max_length=255)
    last_revision_number = models.CharField(max_length=255)
    ftp_server = models.CharField(max_length=255)
    ftp_username = models.CharField(max_length=255)
    ftp_password = models.CharField(max_length=255)
    ftp_folder = models.CharField(max_length=255)

class CategoryMapping(models.Model):
    erp_id = models.CharField(max_length=255, null=True)
    woocommerce_id = models.IntegerField(null=True)

class ConsoleMessage(models.Model):
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    
    def __str__(self):
        return self.store_domain