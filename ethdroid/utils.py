import re
import requests
import logging
import time

from decimal import Decimal

from ethdroid.config import ETHPLORER_API_URL, ETHERSCAN_API_URL, LENGTH_WALLET_ADDRESS, MAX_MESSAGE_LENGTH, CRYPTOCOMPARE_API_URL
from ethdroid.languages import *
from ethdroid.reply_markups import reply_markup_en, reply_markup_es, reply_markup_ru, \
    reply_markup_back_en, reply_markup_back_es, reply_markup_back_ru

# start logging to the file of current directory or print it to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
module_logger = logging.getLogger(__name__)

# start logging to the file with log rotation at midnight of each day
# import os
#
# from logging.handlers import TimedRotatingFileHandler
#
# formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
# handler = TimedRotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + '/../ethdroidbot.log',
#                                    when='midnight',
#                                    backupCount=10)
# handler.setFormatter(formatter)
# module_logger = logging.getLogger(__name__)
# module_logger.addHandler(handler)
# module_logger.setLevel(logging.INFO)
# end of log section


price_ethusd = 0.0
price_ethbtc = 0.0


# to put correct conversation/menu language
def set_usr_language_array(language_code):

    if language_code == 'ru' or language_code == 'ru-RU':
        usr_language_array = RUSSIAN

    elif language_code == 'es' or language_code == 'es-ES':
        usr_language_array = SPANISH

    else:
        usr_language_array = ENGLISH

    return usr_language_array


# to put correct keyboard language
def set_user_usr_keyboard(language_code, usr_keyboard_type=''):

    if usr_keyboard_type == 'go_back':
        if language_code == 'ru' or language_code == 'ru-RU':
            usr_keyboard = reply_markup_back_ru

        elif language_code == 'es' or language_code == 'es-ES':
            usr_keyboard = reply_markup_back_es

        else:
            usr_keyboard = reply_markup_back_en

    else:
        if language_code == 'ru' or language_code == 'ru-RU':
            usr_keyboard = reply_markup_ru

        elif language_code == 'es' or language_code == 'es-ES':
            usr_keyboard = reply_markup_es

        else:
            usr_keyboard = reply_markup_en

    return usr_keyboard


# checks if user has a gap in NUMBER_OF_WALLETS to add one more
def is_full_wallets_list(user_object):

        # True when: * user has a gap in NUMBER_OF_WALLETS to add one more
        if len(user_object['usr_wallets']) < NUMBER_WALLETS:
            return True


# the functions for logging handlers
def send_to_log(update, msg_type='command'):

    if msg_type == 'scheduler':

        module_logger.info("Scheduler wallets balance changes start")

    elif update:

        usr_message = str(update.effective_message.text) if update.effective_message.text else 'None'

        usr_name = update.effective_message.from_user.first_name
        if update.effective_message.from_user.last_name:
            usr_name += ' ' + update.effective_message.from_user.last_name

        if update.effective_message.from_user.username:
            usr_name += ' (@' + update.effective_message.from_user.username + ')'

        usr_chat_id = str(update.effective_message.from_user.id) if update.effective_message.from_user.id else 'None'

        module_logger.info("Has received a {} \"{}\" from user {}, with id {}"
                           .format(msg_type, usr_message, usr_name, usr_chat_id))


# the request for ethereum API
def api_check_balance(bot, usr_wallet_address):

    url = ETHPLORER_API_URL.format(usr_wallet_address)

    request_error = False
    request_error_msg = ''
    response = ''

    headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'}

    try:
        response = requests.get(url, headers=headers, timeout=10)

    except requests.exceptions.RequestException as e:
        request_error = True
        request_error_msg = str(e)

        module_logger.info("API request URL: %s", url)

    if not request_error and response.status_code == requests.codes.ok:

        # extract a json from response to a class "dict"
        response_dict = response.json()

        return response_dict

    else:

        if response:
            request_error_msg += ' ' + response

        module_logger.error('Error while request API: "%s". Error code: "%s"' % (url, response))
        # TODO send here a message to admin to inform about a trouble


# form the text message with individual wallet address information
def text_wallet_info(usr_lang_code, usr_wallet_api_dict):

    global price_ethusd

    usr_language_array = set_usr_language_array(usr_lang_code)

    address = usr_wallet_api_dict['address']

    str_eth_price = ''

    # check ETH balance & price
    eth_balance = round(Decimal(usr_wallet_api_dict['ETH']['balance']), 9).normalize()

    if price_ethusd:

        str_eth_price = ' `($' + str('%.2f' % (eth_balance * price_ethusd)) + ')`'

    # check all tokens balance & price
    if 'tokens' in usr_wallet_api_dict:

        all_tokens_balance = '\n' + usr_language_array['TXT_ETH_TOKENS']

        for token in usr_wallet_api_dict['tokens']:

            ############  TOKEN BALANCE
            # to convert a balance into a correct form to show
            token_balance = Decimal(token['balance']) / 10 ** int(token['tokenInfo']['decimals'])

            if (token_balance * 1000 - int(token_balance * 1000)) == 0:

                # token_balance = '%.2f' % token_balance
                str_token_balance = str(token_balance)

                str_token_balance = str_token_balance.rstrip('0').rstrip('.')\
                    if '.' in str_token_balance else str_token_balance

            else:

                str_token_balance = str(round(token_balance, 9)).rstrip('0')

            ############  TOKEN PRICE
            str_token_price = ''

            if type(token['tokenInfo']['price']) is dict and 'rate' in token['tokenInfo']['price'] \
                    and token['tokenInfo']['price']['rate']:

                str_token_price = ' `($' + str('%.2f' % (token_balance * Decimal(token['tokenInfo']['price']['rate']))) + ')`'

            ############  TOKEN NAME
            if token['tokenInfo']['name']:

                str_token_name = token['tokenInfo']['name']

            else:

                str_token_name = eth_address_short(token['tokenInfo']['address'])

            ############  TOKEN SYMBOL
            if token['tokenInfo']['symbol']:

                str_token_symbol = token['tokenInfo']['symbol']

            else:

                str_token_symbol = '...'

            ############  FINAL ONE TOKEN STRING INFORMATION
            all_tokens_balance += '\n`' + str_token_name\
                                  + '` (*' + str_token_symbol + '*): '\
                                  + str_token_balance + str_token_price

    else:

        all_tokens_balance = '\n' + usr_language_array['TXT_ETH_TOKENS_EMPTY']

    msg_text = '\n' + usr_language_array['TXT_ETH_ADDRESS']\
               + '*' + eth_address_short(address)\
               + '*\n`Ethereum` (*ETH*): '\
               + str(eth_balance) + str_eth_price\
               + '\n' + all_tokens_balance + \
               '\n`-------------------------`'

    return msg_text


# to check a string is a really an ethereum address
def is_valid_eth_address(usr_msg_text):

    if re.search('^0x[a-zA-Z0-9]{40}', usr_msg_text) and len(usr_msg_text) == LENGTH_WALLET_ADDRESS:
        return True


# to parse current ETHEREUM usd and btc prices
def api_check_eth_price(bot, job):

    global price_ethusd, price_ethbtc

    request_error = False
    request_error_msg = ''
    response = ''

    headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'}

    try:
        response = requests.get(CRYPTOCOMPARE_API_URL, headers=headers, timeout=10)

    except requests.exceptions.RequestException as e:
        request_error = True
        request_error_msg = str(e)

    module_logger.info("API request URL: %s", "min-api.cryptocompare.com")

    if not request_error and response.status_code == requests.codes.ok and 'Response' not in response.json():

        # extract a json from response to a class "dict"
        response_dict = response.json()

        price_ethusd = round(Decimal(response_dict['USD']), 2).normalize()
        price_ethbtc = round(Decimal(response_dict['BTC']), 6).normalize()

    else:

        if response:
            request_error_msg += ' ' + response.json()['message']

        module_logger.error('Error while request min-api.cryptocompare.com API. Error code: "%s"' % request_error_msg)
        # TODO send here a message to admin to inform about a trouble


# to compare state of ETH balance and tokens an ethereum address
def eth_wallet_changes(usr_wallet, usr_wallet_api_dict):

    wallet_changes = []

    # tested OK: to check ETH balance
    if usr_wallet_api_dict['ETH']['balance'] != usr_wallet['balance']:

        wallet_changes.append({'symbol': 'ETH',
                              'old_balance': usr_wallet['balance'],
                               'new_balance': usr_wallet_api_dict['ETH']['balance']})

        #############################################    UPDATE  initial received usr_wallet object
        usr_wallet.update({'balance': usr_wallet_api_dict['ETH']['balance']})

    # to check TOKENS balance
    if 'tokens' in usr_wallet_api_dict:

        # tested OK: if BD-wallet already has some tokens
        if len(usr_wallet['tokens']) > 0:

            new_wallet_bd_tokens = []

            # to create new token's list to compare with old token's list then
            # and update it to BD then
            for token_response in usr_wallet_api_dict['tokens']:

                # 2018-08-13 changes to remove the problem of
                # e.g. "ZIL: 0 => 0"
                # when ethplorer.io responses with an old token that already doesn't exists in the wallet
                if token_response['balance'] > 0:

                    new_wallet_bd_tokens.append({'address': token_response['tokenInfo']['address'],
                                             'symbol': token_response['tokenInfo']['symbol'],
                                             'decimals': token_response['tokenInfo']['decimals'],
                                             'balance': token_response['balance']})

            # it's my pain ---- START - is is a hard compare logic to show token's difference
            for new_token in new_wallet_bd_tokens:

                # use case: it is a token which balance was changed
                if any(d['address'] == new_token['address'] and d['balance'] != new_token['balance'] for d in usr_wallet['tokens']):

                    wallet_changes.append({'symbol': new_token['symbol'],
                                          'old_balance': [balance['balance'] for balance in usr_wallet['tokens'] if balance['address'] == new_token['address']][0],
                                           'new_balance': new_token['balance'],
                                           'decimals': new_token['decimals']})

                # use case: it is a new token in the api wallet token's list
                elif not any(d['address'] == new_token['address'] for d in usr_wallet['tokens']):

                    wallet_changes.append({'symbol': new_token['symbol'],
                                          'old_balance': 0,
                                           'new_balance': new_token['balance'],
                                           'decimals': new_token['decimals']})

            # use case: for token which was deleted from BD-wallet token's list
            for old in usr_wallet['tokens']:

                if not any(d['address'] == old['address'] for d in new_wallet_bd_tokens):
                    wallet_changes.append({'symbol': old['symbol'],
                                          'old_balance': old['balance'],
                                           'new_balance': 0,
                                           'decimals': old['decimals']})

            # it's my pain ---- END

            # after all tokens changes old token's array to update it then
            usr_wallet['tokens'] = new_wallet_bd_tokens

        # tested OK: use case: if BD-wallet didn't have any token yet
        else:

            for token_response in usr_wallet_api_dict['tokens']:

                wallet_changes.append({'symbol': token_response['tokenInfo']['symbol'],
                                      'old_balance': 0.0,
                                       'new_balance': token_response['balance'],
                                       'decimals': token_response['tokenInfo']['decimals']})

                usr_wallet['tokens'].append({'address': token_response['tokenInfo']['address'],
                                             'symbol': token_response['tokenInfo']['symbol'],
                                             'decimals': token_response['tokenInfo']['decimals'],
                                             'balance': token_response['balance']})

    # tested OK: use case: if the api wallet already doesn't have any token)
    else:

        if 'tokens' in usr_wallet:

            for token_DB in usr_wallet['tokens']:

                wallet_changes.append({'symbol': token_DB['symbol'],
                                      'old_balance': token_DB['balance'],
                                       'new_balance': 0.0,
                                       'decimals': token_DB['decimals']})

            del usr_wallet['tokens'][:]

    return {'usr_wallet': usr_wallet, 'wallet_changes': wallet_changes}


# form the text message with only change wallet balances
def text_wallet_changes(usr_language_array, wallet_changes, wallet_address=''):

    # wallet_address is used to show wallet info with its address,
    # is a use case of scheduler request of wallet changes
    if wallet_address:

        msg_text = '\n' + usr_language_array['TXT_ETH_ADDRESS'] \
                    + '*' + eth_address_short(wallet_address) \
                    + '*\n`-------------------------`'

    else:

        msg_text = '\n' + usr_language_array['TXT_WALLET_UPDATES']

    # check all changes items (ETH and/or tokens)
    for item in wallet_changes:

        # balance of ETH is counted in different form without use of 'decimals'
        if item['symbol'] == 'ETH':

            old_eth_balance = round(Decimal(item['old_balance']), 9).normalize()
            new_eth_balance = round(Decimal(item['new_balance']), 9).normalize()

            msg_text += '\n*' + item['symbol'] + '*: ' + '`' + str(old_eth_balance)\
                        + ' => ' + str(new_eth_balance) + '`'

        # balances of other tokens
        else:

            ######## old_balance
            old_token_balance = Decimal(item['old_balance']) / 10 ** int(item['decimals'])

            if (old_token_balance * 1000 - int(old_token_balance * 1000)) == 0:

                # token_balance = '%.2f' % token_balance
                str_old_token_balance = str(old_token_balance)

                str_old_token_balance = str_old_token_balance.rstrip('0').rstrip('.')\
                    if '.' in str_old_token_balance else str_old_token_balance

            else:

                str_old_token_balance = str(round(old_token_balance,9)).rstrip('0')

            ######## new_balance
            new_token_balance = Decimal(item['new_balance']) / 10 ** int(item['decimals'])

            if (new_token_balance * 1000 - int(new_token_balance * 1000)) == 0:

                # token_balance = '%.2f' % token_balance
                str_new_token_balance = str(new_token_balance)

                str_new_token_balance = str_new_token_balance.rstrip('0').rstrip('.') \
                    if '.' in str_new_token_balance else str_new_token_balance

            else:

                str_new_token_balance = str(round(new_token_balance, 9)).rstrip('0')

            msg_text += '\n*' + item['symbol'] + '*: ' + '`' + str_old_token_balance \
                        + ' => ' + str_new_token_balance + '`'

    return msg_text + '\n`-------------------------`\n'


# to show only 6 characters from start and from end of the Ethereum (token) address
def eth_address_short(eth_address):

    return eth_address[:6] + '....' + eth_address[-6:]


# to show current ETH price in title of a message
def show_eth_price(usr_language_array):

    global price_ethusd, price_ethbtc

    if price_ethusd and price_ethbtc:

        price_ethereum = usr_language_array['TXT_PRICE'] \
                         + '`$' + str(price_ethusd) \
                         + '` (' + str(price_ethbtc) + ' BTC)' \
                         + '\n`-------------------------`\n'

        return price_ethereum

    else:

        return ''


# to split long message for shorter parters, see github issue:
# https://github.com/python-telegram-bot/python-telegram-bot/issues/768#issuecomment-368349130
def send_message(bot, chat_id, text: str, **kwargs):

    if len(text) <= MAX_MESSAGE_LENGTH:
        return bot.send_message(chat_id, text, **kwargs)

    parts = []

    while len(text) > 0:

        if len(text) > MAX_MESSAGE_LENGTH:

            part = text[:MAX_MESSAGE_LENGTH]
            first_lnbr = part.rfind('\n')

            if first_lnbr != -1:
                parts.append(part[:first_lnbr])
                text = text[first_lnbr:]

            else:
                parts.append(part)
                text = text[MAX_MESSAGE_LENGTH:]

        else:
            parts.append(text)
            break

    msg = None

    for part in parts:

        msg = bot.send_message(chat_id, part, **kwargs)
        time.sleep(1)

    return msg  # return only the last message
