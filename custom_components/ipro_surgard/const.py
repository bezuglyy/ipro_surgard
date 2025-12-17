DOMAIN = "ipro_surgard"
NAME = "IPRO SurGard"

CONF_LISTEN_HOST = "listen_host"
CONF_LISTEN_PORT = "listen_port"
CONF_MAX_ZONES = "max_zones"
CONF_OFFLINE_TIMEOUT = "offline_timeout"

# Optional SMS notifications via GOIP4 integration service goip4.send_sms
CONF_SMS_ENABLE = "sms_enable"
CONF_SMS_LINE = "sms_line"
CONF_SMS_PHONE = "sms_phone"
CONF_SMS_MSG_ARM = "sms_msg_arm"
CONF_SMS_MSG_DISARM = "sms_msg_disarm"
CONF_SMS_COOLDOWN = "sms_cooldown"
CONF_SMS_OBJECT_FILTER = "sms_object_filter"

DEFAULT_LISTEN_HOST = "0.0.0.0"
DEFAULT_LISTEN_PORT = 6601
DEFAULT_MAX_ZONES = 64
DEFAULT_OFFLINE_TIMEOUT = 300  # seconds

DEFAULT_SMS_ENABLE = False
DEFAULT_SMS_LINE = 1
DEFAULT_SMS_PHONE = ""
DEFAULT_SMS_MSG_ARM = "O1"
DEFAULT_SMS_MSG_DISARM = "O0"
DEFAULT_SMS_COOLDOWN = 10  # seconds
DEFAULT_SMS_OBJECT_FILTER = ""

SIGNAL_NEW_OBJECT = "ipro_surgard_new_object"
SIGNAL_NEW_ZONE = "ipro_surgard_new_zone"
SIGNAL_OBJECT_UPDATE = "ipro_surgard_object_update"

# ContactID / SurGard string format (see IPRO-12 manual):
# 5000 18AAAAQXXXYYZZZ  -> 5 + receiver(2) + line(1) + 18 + object(4..10) + Q(E|R) + code(3) + part(2) + zone(3)
