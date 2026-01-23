from flask import Flask, render_template, request, jsonify, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm.attributes import flag_modified
from better_profanity import profanity
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func
from flask_migrate import Migrate
import os
import math
import shlex
import secrets
import random
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
mods = [5, 7, 78, 62, 35]
banned = [129, 130, 131, 132, 105]
#init app
app = Flask(__name__)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "connect_args": {
        "sslmode": "require"
    }
}
app.config['SESSION_COOKIE_SECURE'] = True
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'mysql+pymysql://globalchat:A570805m@globalchat.mysql.pythonanywhere-services.com'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '234g52h3g48hq34wg879g4hq3v89rg98gfq398u4gfbeqrwb08urgu9q34gq03843whg5ub')
bad_words = profanity.load_censor_words()
db = SQLAlchemy(app)
migrate = Migrate(app, db)

limiter = Limiter(app=app, key_func=get_remote_address, storage_uri="memory://")
@app.route('/health')
def health_check():
    return "OK", 200

#init db
class Users(db.Model):
    userid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(150))
    isguest = db.Column(db.Boolean)
    ismuted = db.Column(db.Boolean)
    globes = db.Column(db.Integer, default=0)
    cbc = db.Column(db.BigInteger, default=0)
    equipped_color = db.Column(db.String(20), default="Black")
    equipped_image = db.Column(db.String(200), default=None)
    purchases_today = db.Column(db.Integer, default=0)
    last_purchase_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    total_clicks = db.Column(db.Integer, default=0)
    def setpassword(self, password):
        self.password = password
    def checkpassword(self, password):
        return (self.password == password)
class Item(db.Model):
    __tablename__ = 'itemtable'
    item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    info = db.Column(db.String(1500), nullable=False)
    itemtype = db.Column(db.String(50))
    rarity = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=False)
    sell_price = db.Column(db.Integer, default=0)
class SystemConfig(db.Model):
    __tablename__ = 'system_configs'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(JSONB)

class Inventory(db.Model):
    __table_args__ = (db.UniqueConstraint('userid', 'item_id', name='_user_item_uc'),)
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.userid'))
    item_id = db.Column(db.Integer, db.ForeignKey('itemtable.item_id'), nullable=False)
    count = db.Column(db.Integer, default=0)
    item = db.relationship('Item', backref='owners')
class Message(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.userid'))
    text = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    room_id = db.Column(db.Integer, default=0, index=True)
class ClickCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=1)



@app.before_request
def force_ssl_param():
    if request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url
        if '?' in url:
            return redirect(f"{url}&ssl_required=true", code=301)
        else:
            return redirect(f"{url}?ssl_required=true", code=301)




@app.route('/')
def route():
    session.permanent = True
    if session.get('userid'):
        return render_template("/documentation.html")
    else:
        newuser = Users(username=f"temp {datetime.utcnow().timestamp()}", password=None, isguest=True)
        db.session.add(newuser)
        db.session.commit()
        session['userid'] = newuser.userid
        newuser.username = (f"Guest_{newuser.userid}")
        db.session.commit()
        return render_template("/documentation.html")




@app.route('/sitemap.xml', methods=['GET'])
def sitemap():

    pages = []

    hash_routes = ["overview", "topology", "api", "deployment"]


    base_url = "https://systemnodesync.dpdns.org"

    for route in hash_routes:
        pages.append({
            "loc": f"{base_url}/#{route}",
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "priority": "0.80"
        })


    sitemap_xml = render_template('sitemap.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"

    return response
from flask import Response

@app.route('/robots.txt')
def robots_txt():

    content = (
        "User-agent: *\n"
        "Disallow: /api/v1/internal/\n"
        "Allow: /\n\n"
        "Sitemap: https://systemnodesync.dpdns.org/sitemap.xml"
    )
    return Response(content, mimetype='text/plain')
@app.route('/api/v1/system/heartbeat/state')
def checkpanic():
    config = SystemConfig.query.filter_by(key='panic_switch').first()
    if config:
        return jsonify(config.value)
    return jsonify({"integrity_check": 0}), 404
@app.route('/api/v1/internal/admin/gatekeeper')
def toggle_panic():
    config = SystemConfig.query.filter_by(key='panic_switch').first()
    current_state = config.value.get('integrity_check', 0)
    new_state = 1 if current_state == 0 else 0
    config.value['integrity_check'] = new_state
    flag_modified(config, "value")
    db.session.commit()
    return f"Panic Mode: {'ENABLED' if new_state == 1 else 'DISABLED'}"
PACK_CONFIG = {
    'color': {'base_price': 150, 'scaling': 1.02, 'item_type': 'color'},
    'shape':  {'base_price': 500, 'scaling': 1.0, 'item_type': 'shape'},

}
#IMPORTANT: ROUTE MAPPING:
'''

/send_message,/api/v1/internal/transport/buffer/stream-push
/receive_message,/api/v1/internal/transport/buffer/stream-fetch
/register,/sys/auth/provisioning/node-enrollment
/login,/sys/auth/session/token-negotiation
/shop,/internal/assets/resource-catalog/deployment-manifest
/purchase,/api/v1/transactional/resource-allocation/commit
/item_details/<id>,/api/v1/metadata/schema/object-descriptor/<int:id>
/get_price,/api/v1/system/scaling/load-coefficient
/inc_click_counter,/api/v1/telemetry/heartbeat/delta-increment
/inventory,/sys/local-storage/mount-points/registry
/user/inventory,/api/v3/user-profile/cache/sync-manifest
/equip_color,/sys/env/runtime/ui-configuration/set-preference
/sell_color,/api/v1/assets/liquidation/deprovision-resource
/user/info, /api/v2/user-profile/cache/sync-manifest
/chat, /api/v1/session/sync/view-instance.html
'''

def get_metadata():

    terms = [
        "reconciliation layer", "node latency", "TCP/IP handshake",
        "distributed ledger", "VPC peering", "TLS 1.3 encryption",
        "packet loss mitigation", "buffer overflow protection",
        "high-availability cluster", "heartbeat signal"
    ]
    return " ".join(random.choice(terms) for _ in range(1200))
@app.route('/api/v1/session/sync/view-instance.html')
def mainpage():
    metadata = get_metadata()
    return render_template("/chat.html", system_description=metadata)

@app.route('/changelog')
def changelog():
    return render_template("/changelog.html")
#tool for later
@app.route('/api/v2/user-profile/cache/sync-manifest')
def userinfo():
    tusername = request.args.get('username')
    if tusername:
        user = Users.query.filter_by(username=tusername).first()
    else:
        user = Users.query.get(session.get('userid'))
    return jsonify({
        "userid": user.userid,
        "username": user.username,
        "isguest": user.isguest,
        "globes": user.globes,
        })


@app.route('/api/v1/internal/telemetry/nodes/reconciliation-buffer/system-diagnostics')
def routeclick():
    return render_template("/click.html")
@app.route('/api/v1/internal/transport/buffer/stream-push', methods=['POST'])
def send_msg():
    uid = session.get('userid')
    user = Users.query.get(uid)
    message_text = request.form.get('message_text')
    room_id = request.form.get('room_id', 0, type=int)
    if user.ismuted:
        return jsonify({"error": "You are muted"}), 403
    if uid in banned: #banned ids
        user.isguest = False
        db.session.add(Message(userid=uid, text=message_text, room_id=room_id))
        db.session.commit()
        return jsonify({"status": "success"}), 201
    last_msg = Message.query.filter_by(userid=uid).order_by(Message.timestamp.desc()).first()
    if last_msg and last_msg.text == message_text:
        return jsonify({"status": "error", "message": "Duplicate message ignored"}), 200
    if user.ismuted or profanity.contains_profanity(user.username):
        return jsonify({"status": "success"}), 201
    message_text = profanity.censor(message_text)
    if '*' in message_text or "nigg" in message_text.lower():
        db.session.add(Message(userid=1, text=f"{user.username}, sorry you can't do that", room_id=room_id))
        db.session.commit()
        return jsonify({"status": "success"}), 201
    if '<' in message_text or '>' in message_text:
        if uid == 5:
            db.session.add(Message(userid=uid, text=message_text, room_id=room_id))
            db.session.commit()
        else:
            db.session.add(Message(userid=1, text=str(user) + ", sorry you can't do that", room_id=room_id))
            db.session.commit()
            return jsonify({"status": "error", "message": "HTML tags not allowed"}), 400
    if message_text.startswith('/'):
        if uid in mods:
            if message_text.startswith("/panic"):

                status_msg = toggle_panic()
                db.session.add(Message(userid=1, text=f"SYSTEM: {status_msg}", room_id=room_id))
                db.session.commit()
                return jsonify({"status": "success", "message": "Panic toggled"}), 201
            if message_text.startswith("/mute"):
                splittext = message_text.split(None, 2)
                muted_username = splittext[1].strip().replace('"', ' ')
                reason = splittext[2] if len(splittext) > 2 else ""

                user = Users.query.filter_by(username=muted_username).first()
                if user:
                    user.ismuted = True
                    db.session.add(Message(userid=1, text=f"{user.username} has been muted. Reason: {reason}", room_id=room_id))
                    db.session.commit()
                else:
                    db.session.add(Message(userid=1, text=f"Mute Error: User '{muted_username}' not found.", room_id=room_id))
                    db.session.commit()
            elif message_text.startswith("/unmute"):
                splittext = message_text.split(None, 1)
                target_username = splittext[1].strip().replace('"', ' ')

                tuser = Users.query.filter_by(username=target_username).first()
                if tuser:
                    tuser.ismuted = False
                    db.session.add(Message(userid=1, text=f"{user.username} has been unmuted.", room_id=room_id))
                    db.session.commit()
                else:
                    db.session.add(Message(userid=1, text=f"Unmute Error: User '{target_username}' not found.", room_id=room_id))
                    db.session.commit()




    else:
        db.session.add(Message(userid=uid, text=message_text, room_id=room_id))
        db.session.commit()
    return jsonify({"status": "success"}), 201
@app.route('/api/v1/internal/transport/buffer/stream-fetch', methods=['GET'])
def receive_msg():
    curruid = session.get('userid')


    results = db.session.query(Message, Users, Item)\
        .join(Users, Message.userid == Users.userid)\
        .outerjoin(Item, Users.equipped_color == Item.name)\
        .filter(Message.room_id == 0) \
        .filter((~Message.userid.in_(banned)) | (Message.userid == curruid))\
        .order_by(Message.timestamp.desc()).limit(100).all()

    results.reverse()
    return jsonify([{'userid': msg.userid,
    'username': user.username,
    'text': msg.text,
    'colorinfo': item.info if item else "color: black",
    'level': item.rarity if item else 0,
    'timestamp': msg.timestamp.timestamp()} for msg, user, item in results])



@app.route('/sys/auth/provisioning/node-enrollment', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    username = request.form.get('username', '').strip()
    password = request.form.get('password')
    if session.get('userid'):
        uid = session.get('userid')
    else:
        uid = None
    if not uid:
        return jsonify({"error": "no session"}), 401
    if not username or not password:
        return jsonify({"error": "invalid username or password"}), 400
    if profanity.contains_profanity(username) or "nigg" in username:
        return jsonify({"error": "username must be appropriate"}), 400
    if Users.query.filter_by(username=username).first():
        return jsonify({"error": "username is already taken"}), 409
    user = db.session.get(Users, uid)
    if user and user.isguest:
        user.isguest = False
        user.setpassword(password)
        user.username = username
        db.session.commit()
        return jsonify({"status": "success", "message": "Account created!"}), 201
    else:

        return jsonify({"error": "user is already registered"}), 400

@app.route('/sys/auth/session/token-negotiation', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        user = Users.query.filter_by(username=username).first()
        if user:
            if user.checkpassword(password):
                session.permanent = True
                session['userid'] = user.userid
                return jsonify({"status": "success", "message": "Logged in!"}), 201
            else:
                return jsonify({"error": "Invalid password"}), 401
        else:
            return jsonify({"error": "Invalid username"}), 401
    return(render_template("login.html"))

@app.route('/internal/assets/resource-catalog/deployment-manifest')
def shop():
    return render_template("shop.html")

@app.route('/api/v1/metadata/schema/object-descriptor/<int:id>')
def getiteminfo(id):
    item = Item.query.get_or_404(id)
    return {
        "item_id": item.item_id,
        "name": item.name,
        "info": item.info,
        "itemtype": item.itemtype,
        "rarity": item.rarity,
        "weight": item.weight,
        "active": item.active
    }

@app.route('/api/v1/system/scaling/load-coefficient/<pack_id>')
def get_price(pack_id):
    config = PACK_CONFIG.get(pack_id)
    if not config: return jsonify({"error": "Invalid pack"}), 400.
    user = Users.query.get(session.get('userid'))
    if not user: return jsonify({"price": config['base_price']})
    now = datetime.now(timezone.utc)
    if user.last_purchase_time is None or user.last_purchase_time.date() < now.date():
        purchases = 0
    else:
        purchases = user.purchases_today
    base = config['base_price']
    rate = config['scaling']
    return jsonify({"price": int(base * (rate ** purchases))})
@app.route('/api/v1/transactional/resource-allocation/commit/<pack_id>', methods=["POST"])
def purchase(pack_id):
    userid = session.get('userid')
    user = Users.query.get(userid)
    if not user: return jsonify({"message": "User not found"}), 401
    config = PACK_CONFIG.get(pack_id)
    if not config: return jsonify({"message": "Invalid Pack"}), 400
    data = request.get_json(silent=True) or {}
    batch_count = int(data.get('batch_count', 1))
    items_won = []
    time = datetime.now(timezone.utc)

    if user:
        if user.last_purchase_time is None or user.last_purchase_time.date() < time.date():
            user.purchases_today = 0

        user.last_purchase_time = time

        results = db.session.query(Item.item_id, Item.name, Item.weight, Item.info)\
           .filter(Item.active == True, Item.itemtype == config['item_type'])\
           .order_by(Item.item_id).all()

        info = {r.item_id: {"name": r.name, "info": r.info} for r in results}
        rng = secrets.SystemRandom()
        item_ids = [r.item_id for r in results]
        weights = [r.weight for r in results]

        for _ in range(batch_count):
            curr_price = int(config['base_price'] * (config['scaling'] ** user.purchases_today))
            if user.globes >= curr_price:
                user.globes -= curr_price
                user.purchases_today += 1
                bought_id = rng.choices(item_ids, weights=weights, k=1)[0]
                items_won.append({
                    "name": info[bought_id]["name"],
                    "info": info[bought_id]["info"]
                })

                in_inv = Inventory.query.filter_by(userid=userid, item_id=bought_id).first()
                if in_inv:
                    in_inv.count += 1
                else:
                    db.session.add(Inventory(userid=userid, item_id=bought_id, count=1))
            else:
                if items_won:
                    break
                return jsonify({"status": "Error", "message": "Not enough globes!"}), 401

        db.session.commit()
        next_price = int(config['base_price'] * (config['scaling'] ** user.purchases_today))
        return jsonify({
            "status": "Success",
            "new_balance": user.globes,
            "items_won": items_won,
            "won_item_name": items_won[-1]["name"] if items_won else None,
            "info": items_won[-1]["info"] if items_won else "",
            "price": next_price
        })


def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True
@app.route('/api/v1/telemetry/heartbeat/delta-increment', methods=['GET', 'POST'])
@limiter.limit("15 per second")
def inc_click_counter():
    counter = (ClickCount.query.get(1) or ClickCount(id=1, count=0))
    user = Users.query.get(session.get('userid'))
    is_milestone = False
    if request.method == 'POST':
        if not user:
            return jsonify({"error": "user not found"}), 404
        counter.count += 1
        count = counter.count
        db.session.commit()
        root = math.isqrt(count)
        if root * root == count:
            user.globes += (root * 8)
        if is_prime(count):
            user.globes += int(math.log(count) * 4)
        if is_prime(count - 2):
            user.globes += int(math.log(count) * 8)
        if random.random() < 0.001:
            user.globes += random.randint(100, 500)

        if str(count).endswith('77') or str(count).endswith('67'):
            user.globes += 25
        if (count > 0) and (((count) & (count - 1)) == 0) or (any(count == 10 ** i for i in range(len(str(count))+ 1))):
            is_milestone = True
            db.session.query(Users).filter(Users.userid != user.userid).update({Users.globes: Users.globes + func.floor(Users.cbc)}, synchronize_session=False)
            db.session.query(Users).update({Users.cbc: 0}, synchronize_session=False)
            db.session.add(Message(userid=1, text=str(user.username if user else "A guest") + " has reached milestone " + str(count) + "!"))
            if user:
                user.globes += count
            db.session.commit()
            if user:
                db.session.expire(user)
                db.session.refresh(user)
        if is_milestone == False and user:
            user.cbc += 1
            db.session.commit()
    count = counter.count
    p2 = 2 ** count.bit_length()
    p10 =  10 ** len(str(count))
    if p2 <= count:
        p2 *= 2
    if p10 <= count:
        p10 *= 10
    next_mstone = min(p2, p10)
    return jsonify({
        "count": count,
        "next_milestone": next_mstone,
        "milestone_reached": is_milestone,
        "globes": user.globes if user else 0
        })

@app.route('/sys/local-storage/mount-points/registry')
def inventory():
    return render_template("inventory.html")
@app.route('/api/v3/user-profile/cache/sync-manifest')
def get_inventory():
    uid = session.get('userid')
    user = Users.query.get(uid)
    if user:
        inv = Inventory.query.filter_by(userid=uid).all()
        useritems = [{"name": slot.item.name, "info": slot.item.info, "count": slot.count, "itemtype": slot.item.itemtype, "rarity": slot.item.rarity, "weight": slot.item.weight} for slot in inv]
        equipped_item = Item.query.filter_by(name=user.equipped_color).first()
        equippedinfo = equipped_item.info if equipped_item else "white"


        return jsonify({
        "status": "Success",
        "items": useritems,
        "equipped_item": user.equipped_color,
        "equipped_info": equippedinfo
    })
    else:
        return jsonify({
        "status": "error: Username could not be found.",
    })
'''
@app.route('/user/message_display')
def msg_color_and_level():
    uid = session.get('userid')
    user = Users.query.get(uid)
    if user:
        equipped_item = Item.query.filter_by(name=user.equipped_color).first()
        if not equipped_item:
            return jsonify({"status": "Success", "level": 0, "colorinfo": "color: #000000;"
    })
        color_info = equipped_item.info
        level = equipped_item.rarity

        return jsonify({
        "status": "Success",
        "level": level,
        "colorinfo": color_info,
    })
    else:
        return jsonify({"status": "error: Username could not be found."})
        '''
@app.route('/sys/env/runtime/ui-configuration/set-preference', methods=["POST"])
def equip_color():
    uid = session.get('userid')
    user = Users.query.get(uid)
    if user:
        color = request.get_json()
        color = color.get('item_name')
        if color:
            user.equipped_color = color
            db.session.commit()
        return jsonify({"status": "Success"})
@app.route('/sys/env/runtime/ui-configuration/set-image', methods=["POST"])
def equip_image():
    uid = session.get('userid')
    user = Users.query.get(uid)
    if user:
        image = request.get_json()
        image = image.get('item_name')
        if image:
            user.equipped_image = image
            db.session.commit()
        return jsonify({"status": "Success"})
@app.route('/api/v1/assets/liquidation/deprovision-resource', methods=["POST"])
def sell_color():
    uid = session.get('userid')
    user = Users.query.get(uid)

    if user:
        color = request.get_json()
        color = color.get('item_name')
        item = Item.query.filter_by(name=color).first()
        inv_entry = Inventory.query.filter_by(userid=user.userid, item_id=item.item_id).first()

        if color and inv_entry:
            inv_entry.count -= 1
            user.globes += item.sell_price
            db.session.commit()
            if inv_entry.count <= 0:
                db.session.delete(inv_entry)
                if user.equipped_color == color:
                    user.equipped_color = "black"
            db.session.commit()
        return jsonify({"status": "Success", "message": f"Sold {color} for {item.sell_price} globes"})
@app.route('/api/v1/session/reconciliation-view.html')
def sync_logs():
    return render_template('sync_logs.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



