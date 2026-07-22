#!/usr/bin/env python3
import requests
import time
from urllib.parse import urlparse

# Your exact list (name: login_url)
SITES = {
    "PCOptimum": "https://www.pcoptimum.ca/login",
    "Pepper": "https://www.pepper.com/login",
    "Shopfully": "https://www.shopfully.com/login",
    "Fidme": "https://www.fidme.com/login",
    "Piggy": "https://www.piggy.eu/login",
    "SparkLoyalty": "https://www.sparkloyalty.com/login",
    "SessionM": "https://www.sessionm.com/login",
    "Paytronix": "https://www.paytronix.com/login",
    "Thanx": "https://www.thanx.com/login",
    "BellyCard": "https://www.bellycard.com/login",
    "Fivestars": "https://www.fivestars.com/login",
    "FetchRewards": "https://www.fetchrewards.com/login",
    "Cardlytics": "https://www.cardlytics.com/login",
    "Figg": "https://www.figg.com/login",
    "Mojorewards": "https://www.mojorewards.com/login",
    "Point.Me": "https://www.point.me/login",
    "TravelFreely": "https://www.travelfreely.com/login",
    "EvReward": "https://www.evreward.com/login",
    "Giftogram": "https://www.giftogram.com/login",
    "Gyft": "https://www.gyft.com/login",
    "Raise": "https://www.raise.com/login",
    "GiftRocket": "https://www.giftrocket.com/login",
    "Egifter": "https://www.egifter.com/login",
    "PerfectGift": "https://www.perfectgift.com/login",
    "GiftCards.com": "https://www.giftcards.com/login",
    "Cardbear": "https://www.cardbear.com/login",
    "Cardcookie": "https://www.cardcookie.com/login",
    "Cardflip": "https://www.cardflip.com/login",
    "Tillo": "https://www.tillo.io/login",
    "Wegift": "https://www.wegift.io/login",
    "Buyatab": "https://www.buyatab.com/login",
    "GiftMall": "https://www.giftmall.co.jp/login",
    "Giftbit.net": "https://www.giftbit.net/login",
    "GiftCards.ca": "https://www.giftcards.ca/login",
    "YourRewardCard": "https://www.yourrewardcard.com/login",
    "VirtualRewardCenter": "https://www.virtualrewardcenter.com/login",
    "MyGiftCardsPlus": "https://www.mygiftcardsplus.com/login",
    "Avios": "https://www.avios.com/login",
    "Nectar": "https://www.nectar.com/login",
    "Nectar360": "https://www.nectar360.co.uk/login",
    "Flybuys": "https://www.flybuys.com.au/login",
    "VelocityFrequentFlyer": "https://www.velocityfrequentflyer.com/login",
    "Qantas": "https://www.qantas.com/login",
    "AsiaRewards": "https://www.asiarewards.com/login",
    "KrisPlus": "https://www.krisplus.com/login",
    "KrisFlyer": "https://www.krisflyer.com/login",
    "AirAsiaRewards": "https://www.airasiarewards.com/login",
    "Pepsi": "https://www.pepsi.com/login",
    "KeurigDrPepper": "https://www.keurigdrpepper.com/login",
    "Nike": "https://www.nike.com/login",
    "Adidas": "https://www.adidas.com/login",
    "Starbucks": "https://www.starbucks.com/login",
    "McDonalds": "https://www.mcdonalds.com/login",
    "BurgerKing": "https://www.burgerking.com/login",
    "Subway": "https://www.subway.com/login",
    "Chipotle": "https://www.chipotle.com/login",
    "Dominos": "https://www.dominos.com/login",
    "Walgreens": "https://www.walgreens.com/login",
    "CVS": "https://www.cvs.com/login",
    "Target": "https://www.target.com/login",
    "SamsClub": "https://www.samsclub.com/login",
    "BestBuy": "https://www.bestbuy.com/login",
    "Macys": "https://www.macys.com/login",
    "Kohls": "https://www.kohls.com/login",
    "Nordstrom": "https://www.nordstrom.com/login",
    "Bloomingdales": "https://www.bloomingdales.com/login",
    "Sephora": "https://www.sephora.com/login",
    "Ulta": "https://www.ulta.com/login",
    "REI": "https://www.rei.com/login",
    "Cabelas": "https://www.cabelas.com/login",
    "BassPro": "https://www.basspro.com/login",
    "DicksSportingGoods": "https://www.dickssportinggoods.com/login",
    "Zappos": "https://www.zappos.com/login",
    "Ebay": "https://www.ebay.com/login",
    "Etsy": "https://www.etsy.com/login",
    "Aliexpress": "https://www.aliexpress.com/login",
    "Temu": "https://www.temu.com/login",
    "Shein": "https://www.shein.com/login",
    "Amazon": "https://www.amazon.com/login",
    "UberEats": "https://www.ubereats.com/login",
    "Doordash": "https://www.doordash.com/login",
    "Grubhub": "https://www.grubhub.com/login",
    "Uber": "https://www.uber.com/login",
    "Expedia": "https://www.expedia.com/login",
    "Booking": "https://www.booking.com/login",
    "Hotels.com": "https://www.hotels.com/login",
    "Priceline": "https://www.priceline.com/login",
    "Travelocity": "https://www.travelocity.com/login",
    "Orbitz": "https://www.orbitz.com/login",
    "Agoda": "https://www.agoda.com/login",
    "Trip.com": "https://www.trip.com/login",
    "VRBO": "https://www.vrbo.com/login",
    "Viator": "https://www.viator.com/login",
    "GetYourGuide": "https://www.getyourguide.com/login",
    "Klook": "https://www.klook.com/login",
    "Tripadvisor": "https://www.tripadvisor.com/login",
    "OpenRice": "https://www.openrice.com/login",
    "PayPal": "https://www.paypal.com/login",
    "Venmo": "https://venmo.com/login",
    "Revolut": "https://www.revolut.com/login",
    "Chime": "https://www.chime.com/login",
    "Discover": "https://www.discover.com/login",
    "AmericanExpress": "https://www.americanexpress.com/login",
    "Mastercard": "https://www.mastercard.com/login",
    "Visa": "https://www.visa.com/login",
    "Stripe": "https://www.stripe.com/login",
    "Klarna": "https://www.klarna.com/login",
    "Afterpay": "https://www.afterpay.com/login",
    "Affirm": "https://www.affirm.com/login",
    "Zip": "https://www.zip.co/login",
    "Splitit": "https://www.splitit.com/login",
    "Shop.app": "https://shop.app/login",
    "Apple": "https://appleid.apple.com/login",
    "Microsoft": "https://login.microsoftonline.com/login",
    "Lenovo": "https://www.lenovo.com/login",
    "Dell": "https://www.dell.com/login",
    "HP": "https://www.hp.com/login",
    "Asus": "https://www.asus.com/login",
    "Nvidia": "https://www.nvidia.com/login",
    "Sony": "https://www.sony.com/login",
    "PlayStation": "https://www.playstation.com/login",
    "Xbox": "https://www.xbox.com/login",
    "Nintendo": "https://www.nintendo.com/login",
    "Steam": "https://steamcommunity.com/login",
    "EpicGames": "https://www.epicgames.com/login",
    "GOG": "https://www.gog.com/login",
    "HumbleBundle": "https://www.humblebundle.com/login",
    "Fanatical": "https://www.fanatical.com/login",
    "GreenManGaming": "https://www.greenmangaming.com/login",
    "CDKeys": "https://www.cdkeys.com/login",
    "Newegg": "https://www.newegg.com/login",
    "MicroCenter": "https://www.microcenter.com/login",
    "B&HPhoto": "https://www.bhphotovideo.com/login",
    "Adorama": "https://www.adorama.com/login",
    "Staples": "https://www.staples.com/login",
    "Office.com": "https://www.office.com/login",
    "Lowe's": "https://www.lowes.com/login",
    "HomeDepot": "https://www.homedepot.com/login",
    "IKEA": "https://www.ikea.com/login",
    "Wayfair": "https://www.wayfair.com/login",
    "Overstock": "https://www.overstock.com/login",
    "Chewy": "https://www.chewy.com/login",
    "Petco": "https://www.petco.com/login",
    "ProFlowers": "https://www.proflowers.com/login",
    "EdibleArrangements": "https://www.ediblearrangements.com/login",
    "FTD": "https://www.ftd.com/login",
    "Teleflora": "https://www.teleflora.com/login",
    "Moonpig": "https://www.moonpig.com/login",
    "FunkyPigeon": "https://www.funkypigeon.com/login",
    "Vistaprint": "https://www.vistaprint.com/login",
    "Canva": "https://www.canva.com/login",
    "Printful": "https://www.printful.com/login",
    "Printify": "https://www.printify.com/login",
    "Redbubble": "https://www.redbubble.com/login",
    "TeePublic": "https://www.teepublic.com/login",
    "Society6": "https://www.society6.com/login",
    "CafePress": "https://www.cafepress.com/login",
    "Spreadshirt": "https://www.spreadshirt.com/login",
    "FineArtAmerica": "https://www.fineartamerica.com/login",
    "Minted": "https://www.minted.com/login",
    "NotOnTheHighStreet": "https://www.notonthehighstreet.com/login",
    "Wowcher": "https://www.wowcher.co.uk/login",
    "Influenster": "https://www.influenster.com/login",
    "BzzAgent": "https://www.bzzagent.com/login",
    "Crowdtap": "https://www.crowdtap.com/login",
    "Pinecone": "https://www.pinecone.com/login",
    "LifePointsPanel": "https://www.lifepointspanel.com/login",
    "YouGov": "https://www.yougov.com/login",
    "Toluna": "https://www.toluna.com/login",
    "IpsosiSay": "https://www.ipsosisay.com/login",
    "Attapoll": "https://www.attapoll.com/login",
    "OnePoll": "https://www.onepoll.com/login",
    "Prolific": "https://www.prolific.com/login",
    "Respondent": "https://www.respondent.io/login",
    "UserInterviews": "https://www.userinterviews.com/login",
    "UserTesting": "https://www.usertesting.com/login",
    "TryMata": "https://www.trymata.com/login",
    "Ferpection": "https://www.ferpection.com/login",
    "PlaytestCloud": "https://www.playtestcloud.com/login",
    "Applause": "https://www.applause.com/login",
    "UTest": "https://www.utest.com/login",
    "TesterWork": "https://www.testerwork.com/login",
    "Validately": "https://www.validately.com/login",
    "ConversionCrimes": "https://www.conversioncrimes.com/login",
    "EnrollApp": "https://www.enrollapp.com/login",
    "TestingTime": "https://www.testingtime.com/login",
    "Checkealos": "https://www.checkealos.com/login",
    "Clickworker": "https://www.clickworker.com/login",
    "Appen": "https://www.appen.com/login",
    "TelusInternational": "https://www.telusinternational.ai/login",
    "FieldAgent": "https://www.fieldagent.net/login",
    "Mobee": "https://www.mobee.com/login",
    "Gigwalk": "https://www.gigwalk.com/login",
    "EasyShift": "https://www.easyshiftapp.com/login",
    "Premise": "https://www.premise.com/login",
    "Streetbees": "https://www.streetbees.com/login"
}

def has_captcha(url):
    try:
        r = requests.get(url, timeout=15, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text.lower()
        # Check for reCAPTCHA / hCaptcha
        patterns = [
            "g-recaptcha",
            "recaptcha",
            "hcaptcha",
            'src="https://www.google.com/recaptcha/',
            'src="https://www.recaptcha.net/recaptcha/',
            'src="https://js.hcaptcha.com/',
            'data-sitekey',
            'data-hcaptcha',
        ]
        for p in patterns:
            if p in html:
                return True
        return False
    except:
        return None

no_captcha = []
with_captcha = []
error = []

print("Scanning login pages...\n")
for name, url in SITES.items():
    print(f"Checking {name}...", end="")
    result = has_captcha(url)
    if result is None:
        print(" ERROR (unreachable)")
        error.append(name)
    elif result:
        print(" CAPTCHA")
        with_captcha.append(name)
    else:
        print(" NO CAPTCHA")
        no_captcha.append(name)
    time.sleep(0.5)

# Save results
with open("no_captcha_list.txt", "w") as f:
    for name in no_captcha:
        f.write(f"{name}: {SITES[name]}\n")

with open("with_captcha_list.txt", "w") as f:
    for name in with_captcha:
        f.write(f"{name}: {SITES[name]}\n")

with open("error_list.txt", "w") as f:
    for name in error:
        f.write(f"{name}: {SITES[name]}\n")

print(f"\n✅ Done.")
print(f"   NO CAPTCHA: {len(no_captcha)} → no_captcha_list.txt")
print(f"   WITH CAPTCHA: {len(with_captcha)} → with_captcha_list.txt")
print(f"   ERROR: {len(error)} → error_list.txt")