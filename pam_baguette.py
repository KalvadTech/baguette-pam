import requests
import time
import qrcode
import yaml
import pwd
import grp


def pam_sm_authenticate(pamh, flags, argv):
    try:
        args = parse_args(argv)
        config = load_config(args["config_file"])
        authorization = make_authorization_request(config)
        print_authentication_promt(pamh, config, authorization)
        token_response = poll_for_token(pamh, config, authorization)
        authorize_user(pamh, config, token_response)
        return pamh.PAM_SUCCESS

    except BaseException as e:
        print(e)


def parse_args(argv):
    args = {"config_file": argv[1] if len(argv) > 1 else None}
    return args


def load_config(file_name):
    if file_name is None:
        file_name = "/etc/pam_baguette/config.yml"
    with open(file_name, "r") as stream:
        return yaml.safe_load(stream)


def make_authorization_request(config):
    device_response = requests.post(
        "{}/api/ciba".format(config["baguette"]["api_endpoint"]),
        data={
            "server_id": config["baguette"]["server"]["id"],
        },
    )

    if "error" in device_response.json():
        raise BaguetteException(
            device_response.json()["error"], device_response.json()["error_description"]
        )
    return device_response.json()


def print_authentication_promt(pamh, config, authorization):
    ciba_token = str(authorization["ciba_token"])
    url = "{}/api/ciba/{}/validate".format(
        config["baguette"]["api_endpoint"], ciba_token
    )
    qr_str = generate_qr(url, config)

    prompt(pamh, config["texts"]["prompt"].format(url=url, qr=qr_str))


def poll_for_token(pamh, config, authorization):
    ciba_token = str(authorization["ciba_token"])

    timeout = authorization["timeout"]
    interval = 1
    while True:
        time.sleep(interval)
        timeout -= interval

        token_response = requests.get(
            "{}/api/ciba/{}".format(config["baguette"]["api_endpoint"], ciba_token),
        )
        if "error" in token_response.json():
            if token_response.json()["error"] == "authorization_pending":
                pass

            else:
                raise BaguetteException(
                    token_response.json()["error"],
                    token_response.json()["error_description"],
                )
        else:
            break

        if timeout < 0:
            send(pamh, "Timeout, please try again")
            raise BaguetteException(
                token_response.json()["error"],
                token_response.json()["error_description"],
            )

    return token_response.json()


def authorize_user(pamh, config, token_response):
    username = token_response.json()["username"]
    try:
        grp.getgrnam(username)
    except KeyError:
        print("Group {} does not exist. Creating it!".format(username))
    try:
        pwd.getpwnam(username)
    except KeyError:
        print("User {} does not exist. Creating it!".format(username))
    pamh.user = username


def generate_qr(str, config):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(str)
    qr.make()

    if config["qr"]["big"]:
        return generate_qr_big(qr.modules, config)
    else:
        return generate_qr_small(qr.modules, config)


def generate_qr_small(modules, config):
    before_line = config["qr"]["before_line"]
    after_line = config["qr"]["after_line"]

    qr_str = before_line
    qr_str += qr_half_char(False, False, config)
    for x in range(0, len(modules[0])):
        qr_str += qr_half_char(False, False, config)
    qr_str += qr_half_char(False, False, config) + after_line + "\n"

    for y in range(0, len(modules) // 2 + 1):
        qr_str += before_line + qr_half_char(False, False, config)
        for x in range(0, len(modules[0])):
            qr_str += qr_half_char(
                modules[y * 2][x],
                modules[y * 2 + 1][x] if len(modules) > y * 2 + 1 else False,
                config,
            )
        qr_str += qr_half_char(False, False, config)
        if y != len(modules) // 2:
            qr_str += after_line + "\n"

    return qr_str


def generate_qr_big(modules, config):
    before_line = config["qr"]["before_line"]
    after_line = config["qr"]["after_line"]

    qr_str = before_line

    qr_str += qr_full_char(False, config)
    for x in range(0, len(modules[0])):
        qr_str += qr_full_char(False, config)
    qr_str += qr_full_char(False, config) + after_line + "\n"

    for y in range(0, len(modules)):
        qr_str += before_line + qr_full_char(False, config)
        for x in range(0, len(modules[0])):
            qr_str += qr_full_char(modules[y][x], config)
        qr_str += qr_full_char(False, config) + after_line + "\n"

    qr_str += before_line + qr_full_char(False, config)
    for x in range(0, len(modules[0])):
        qr_str += qr_full_char(False, config)
    qr_str += qr_full_char(False, config) + after_line

    return qr_str


def qr_half_char(top, bot, config):
    if config["qr"]["inverse"]:
        if top and bot:
            return "\033[40;97m\xE2\x96\x88\033[0m"
        if not top and bot:
            return "\033[40;97m\xE2\x96\x84\033[0m"
        if top and not bot:
            return "\033[40;97m\xE2\x96\x80\033[0m"
        if not top and not bot:
            return "\033[40;97m\x20\033[0m"
    else:
        if top and bot:
            return "\033[40;97m\x20\033[0m"
        if not top and bot:
            return "\033[40;97m\xE2\x96\x80\033[0m"
        if top and not bot:
            return "\033[40;97m\xE2\x96\x84\033[0m"
        if not top and not bot:
            return "\033[40;97m\xE2\x96\x88\033[0m"


def qr_full_char(filled, config):
    if config["qr"]["inverse"]:
        if filled:
            return "\033[40;97m\xE2\x96\x88\xE2\x96\x88\033[0m"
        else:
            return "\033[40;97m\x20\x20\033[0m"
    else:
        if filled:
            return "\033[40;97m\x20\x20\033[0m"
        else:
            return "\033[40;97m\xE2\x96\x88\xE2\x96\x88\033[0m"


def send(pamh, msg):
    return pamh.conversation(pamh.Message(pamh.PAM_TEXT_INFO, msg))


def prompt(pamh, msg):
    return pamh.conversation(pamh.Message(pamh.PAM_PROMPT_ECHO_ON, msg))


class BaguetteException(Exception):
    pass


# Need to implement all methods to fulfill pam_python contract


def pam_sm_setcred(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_acct_mgmt(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_open_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_close_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_chauthtok(pamh, flags, argv):
    return pamh.PAM_SUCCESS
