#!/usr/bin/env python3
import requests
import time
from urllib.parse import urlparse

# List of domains from your message
domains = """
juno.com
netzero.net
verizon.net
frontier.com
frontiernet.net
windstream.net
centurylink.net
embarqmail.com
q.com
sbcglobal.net
pacbell.net
ameritech.net
prodigy.net
flash.net
swbell.net
mindspring.com
peoplepc.com
optonline.net
rcn.com
wowway.com
cableone.net
suddenlink.net
mediacombb.net
epbfi.com
gci.net
hawaiiantel.net
telus.com
mts.net
eastlink.ca
execulink.com
primus.ca
start.ca
teksavvy.com
runbox.no
email.it
inwind.it
tin.it
iol.it
lycos.com
lycos.co.uk
hush.ai
mailbox.com
usa.net
mykolab.com
posteo.net
ecloud.global
mailhostbox.com
mxlogin.com
mailproxsy.com
ukr.net
meta.ua
i.ua
bigmir.net
tut.by
onet.eu
eclipso.eu
mail.be
skynet.be
voo.be
telenet.be
ziggo.nl
xs4all.nl
kpnmail.nl
planet.nl
chello.nl
upcmail.nl
telia.com
telia.se
bredband.net
bahnhof.se
tele2.se
online.no
tiscali.it
tiscali.co.uk
virginmedia.com
btinternet.com
bt.com
talktalk.net
sky.com
plus.net
ee.co.uk
vodafone.co.uk
eir.ie
eircom.net
telus.net
shaw.ca
rogers.com
bell.net
sympatico.ca
videotron.ca
cox.net
comcast.net
xfinity.com
charter.net
spectrum.net
att.net
bellsouth.net
earthlink.net
libero.it
virgilio.it
alice.it
laposte.net
orange.fr
free.fr
sfr.fr
wanadoo.fr
gmx.net
gmx.at
gmx.ch
bluewin.ch
swissonline.ch
protonmail.com
icloud.com
me.com
mac.com
gmail.com
outlook.com
hotmail.com
live.com
msn.com
yahoo.com
ymail.com
rocketmail.com
aol.com
aim.com
fastmail.fm
hey.com
duck.com
startmail.nl
mail.ee
inbox.lv
mail.bg
abv.bg
o2.pl
wp.pl
interia.pl
onet.pl
centrum.cz
atlas.cz
azet.sk
centrum.sk
zoznam.sk
mail.kz
bk.ru
list.ru
inbox.ru
rambler.ru
heartinternet.uk
clouvider.com
exabytes.com
shinjiru.com
hostarmada.com
chemicloud.com
knownhost.com
rosehosting.com
scalahosting.com
verpex.com
cloudways.com
wpengine.com
kinsta.com
flywheelwp.com
pantheon.io
acquia.com
platform.sh
render.com
railway.app
fly.io
vercel.com
netlify.com
heroku.com
oracle.com
ibm.com
alibabacloud.com
tencentcloud.com
huaweicloud.com
yandex.com
mail.ru
naver.com
daum.net
qq.com
163.com
126.com
yeah.net
aliyun.com
exmail.qq.com
worksmobile.com
larksuite.com
feishu.cn
uol.com.br
bol.com.br
terra.com.br
rediffmail.com
mail.com
gmx.com
web.de
seznam.cz
t-online.de
maildrop.cc
burnermail.io
spamgourmet.com
33mail.com
anonaddy.com
firetrust.com
mailfence.com
ctemplar.com
hushmail.com
countermail.com
vfemail.net
luxsci.com
atmail.com
kerio.com
zimbra.com
icewarp.com
open-xchange.com
mailenable.com
smartertools.com
axigen.com
communigate.com
mdaemon.com
afterlogic.com
crossbox.io
roundcube.net
sogo.nu
citadel.org
wildduck.email
stalwartlabs.com
mailu.io
wildbit.com
postalhq.com
mailzy.ai
mailazy.net
turbo-smtp.org
mailrelay.com
dinahosting.com
arsys.es
transip.nl
infomaniak.com
hostpoint.ch
one.com
simply.com
loopia.se
blacknight.com
register365.com
ukfast.co.uk
krystal.uk
20i.com
fasthosts.co.uk
spamhaus.org
spamcop.net
surbl.org
uribl.com
dnswl.org
abusix.com
invaluement.com
proofpoint.com
mimecast.com
barracuda.com
fortinet.com
sophos.com
trendmicro.com
checkpoint.com
broadcom.com
cisco.com
cloudmark.com
vipre.com
vircom.com
hornetsecurity.com
trustifi.com
easydmarc.com
senderscore.org
talosintelligence.com
multirbl.valli.org
dnschecker.org
mailgenius.com
mailtester.ninja
mailforge.ai
maildoso.com
mailflow.com
suped.com
mailop.org
emaillove.com
senderscore.com
mailosaur.com
mailinator.com
ethereal.email
mailnesia.com
guerrillamail.com
temp-mail.org
10minutemail.com
tempmail.plus
tempail.com
yopmail.com
dispostable.com
dropmail.me
inboxes.com
mailcatch.app
fakeinbox.com
dynadot.com
gandi.net
joker.com
hexonet.net
internetbs.net
name.com
networksolutions.com
register.com
iwantmyname.com
easydns.com
ovhcloud.com
scaleway.com
contabo.com
vultr.com
digitalocean.com
linode.com
hetzner.com
exoscale.com
upcloud.com
leaseweb.com
kamatera.com
hostwinds.com
greenarrowemail.com
mailchannels.com
cloudmailin.com
mailazy.com
maileroo.com
sweego.io
emailapi.com
postalserver.io
emailengine.app
mailcow.email
mailinabox.email
modoboa.org
iredmail.org
docker-mailserver.github.io
stalw.art
haraka.github.io
postfix.org
dovecot.org
exim.org
rspamd.com
opendkim.org
openarc.org
apache.org
policyd.org
scrolloutf1.com
iredadmin.org
mailcleaner.org
proxmox.com
ondmarc.redsift.com
uriports.com
mailhardener.com
glockapps.com
mail-tester.com
warmupinbox.com
folderly.com
mailreach.co
lemwarm.com
trulyinbox.com
inboxally.com
mailwarm.com
forwardemail.net
improvmx.com
simplelogin.io
addy.io
migadu.com
fastmail.com
proton.me
tutanota.com
posteo.de
startmail.com
mailbox.org
runbox.com
kolabnow.com
purelymail.com
mxroute.com
zoho.com
googleworkspace.google.com
workspace.microsoft.com
rackspace.com
namecheap.com
opensrs.com
openprovider.com
cloudflare.com
hostinger.com
ionos.com
dreamhost.com
siteground.com
bluehost.com
inmotionhosting.com
a2hosting.com
liquidweb.com
interserver.net
web.com
godaddy.com
pair.com
hover.com
porkbun.com
dynu.com
acoustic.com
maropost.com
e-goi.com
cleverreach.com
mailup.com
vision6.com
cm.com
bloomreach.com
freshworks.com
keap.com
ontraport.com
user.com
sendfox.com
selzy.com
mailshake.com
reply.io
saleshandy.com
instantly.ai
smartlead.ai
quickmail.com
lemlist.com
woodpecker.co
gmass.co
mailmeteor.com
yesware.com
mixmax.com
outreach.io
salesloft.com
close.com
persistiq.com
apollo.io
snov.io
hunter.io
zerobounce.net
neverbounce.com
kickbox.com
verifalia.com
debounce.io
clearout.io
emailable.com
proofy.io
mailboxvalidator.com
millionverifier.com
bouncer.bounce.email
abstractapi.com
mailcheck.ai
mxtoolbox.com
dmarcian.com
valimail.com
powerdmarc.com
sendgrid.com
mailgun.com
resend.com
postmarkapp.com
mailersend.com
smtp2go.com
smtp.com
mailjet.com
brevo.com
elasticemail.com
sparkpost.com
zeptomail.com
courier.com
loops.so
customer.io
emailoctopus.com
socketlabs.com
pepipost.com
sendpulse.com
emaillabs.io
serversmtp.com
mailpace.com
mail.baby
unione.io
useplunk.com
mailtrap.io
sendy.co
emailjs.com
netcorecloud.com
moosend.com
campaignmonitor.com
aweber.com
constantcontact.com
activecampaign.com
getresponse.com
kit.com
omnisend.com
drip.com
sender.net
bird.com
mailerlite.com
benchmarkemail.com
sendx.io
mailmodo.com
engagebay.com
ortto.com
iterable.com
braze.com
blueshift.com
dotdigital.com
""".strip().splitlines()

# Clean and deduplicate
domains = list(set([d.strip() for d in domains if d.strip()]))

# Possible login paths to try (in order of likelihood)
LOGIN_PATHS = [
    "/login",
    "/signin",
    "/auth",
    "/account/login",
    "/en/login",
    "/logon",
    "/user/login",
    "/member/login",
]

def test_login_page(base_url):
    """
    Try multiple login paths until one returns a successful page (status 200)
    then check for captcha.
    """
    for path in LOGIN_PATHS:
        try:
            url = base_url.rstrip('/') + path
            r = requests.get(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                html = r.text.lower()
                # Check for reCAPTCHA indicators
                if "g-recaptcha" in html or "recaptcha" in html:
                    return "CAPTCHA"
                else:
                    return "NO CAPTCHA"
        except Exception:
            continue
    return "UNKNOWN (no login page found)"

def get_base_url(domain):
    # Try common protocols and subdomains
    candidates = [
        f"https://www.{domain}",
        f"https://{domain}",
        f"https://login.{domain}",
        f"https://account.{domain}",
        f"https://my.{domain}",
    ]
    for url in candidates:
        try:
            # Quick HEAD or GET to see if it responds
            r = requests.get(url, timeout=5, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code < 500:
                return url
        except:
            continue
    return None

no_captcha = []
with_captcha = []
unknown = []

print(f"Checking {len(domains)} domains...\n")
for i, domain in enumerate(domains, 1):
    print(f"[{i}/{len(domains)}] Checking {domain}...", end="", flush=True)
    base_url = get_base_url(domain)
    if base_url is None:
        print(" UNKNOWN (site unreachable)")
        unknown.append(domain)
        continue
    result = test_login_page(base_url)
    print(f" {result}")
    if result == "NO CAPTCHA":
        no_captcha.append(domain)
    elif result == "CAPTCHA":
        with_captcha.append(domain)
    else:
        unknown.append(domain)
    time.sleep(0.5)  # Be gentle

# Save results
with open("no_captcha_email_services.txt", "w") as f:
    for d in no_captcha:
        f.write(d + "\n")

with open("with_captcha_email_services.txt", "w") as f:
    for d in with_captcha:
        f.write(d + "\n")

with open("unknown_email_services.txt", "w") as f:
    for d in unknown:
        f.write(d + "\n")

print(f"\n✅ Done.")
print(f"   NO CAPTCHA: {len(no_captcha)} services → saved to no_captcha_email_services.txt")
print(f"   WITH CAPTCHA: {len(with_captcha)} services → saved to with_captcha_email_services.txt")
print(f"   UNKNOWN: {len(unknown)} services → saved to unknown_email_services.txt")