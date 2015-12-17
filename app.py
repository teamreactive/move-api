#!flask/bin/python
import base64
import jwt
import math
import os

from datetime import datetime
from dotenv import Dotenv
from flask import abort, Flask, jsonify, make_response, request, _request_ctx_stack, url_for
from functools import wraps
from sqlalchemy import and_, Column, create_engine, DateTime, desc, ForeignKey, func, Integer, Numeric, Sequence, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from werkzeug.local import LocalProxy

# ###############################################
# ############### Initial config ################
# ###############################################

# Env configuration
env = None
try:
	env = Dotenv('./.env')
	# Auth0 data
	client_id = env['AUTH0_CLIENT_ID']
	client_secret = env['AUTH0_CLIENT_SECRET']
	# DB data
	db_provider = env['DB_PROVIDER']
	db_user = env['DB_USER']
	db_password = env['DB_PASSWORD']
	db_address = env['DB_ADDRESS']
	db_name = env['DB_NAME']
except IOError:
	env = os.environ
# Flask instance
app = Flask(__name__)
# Authentication annotation
current_user = LocalProxy(lambda: _request_ctx_stack.top.current_user)
# Database initialization
engine = create_engine('%s://%s:%s@%s/%s' % (db_provider, db_user, db_password, db_address, db_name), echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# ###############################################
# ################## Constants ##################
# ###############################################

ORDER_MADE = 0
ORDER_ACCEPTED = 1
ORDER_FINISHED = 2

ORDER_STATUS_MESSAGES = [
	'Order made',
	'Order accepted',
	'Order finished'
]

USER_ORDER_LIMIT = 4
STORE_ORDER_LIMIT = 10
OFFER_ORDER_LIMIT = 7

DEFAULT_ORDER_RADIUS = 1

KM_UNIT = 6371

# ###############################################
# ################## DB Models ##################
# ###############################################

class Item(Base):
	# Table name
	__tablename__ = 'items'
	# Table attributes
	id = Column(Integer, Sequence('item_id_seq'), primary_key=True)
	amount = Column(Integer)
	name = Column(String(100))
	# Table relations
	order_id = Column(Integer, ForeignKey('orders.id'))
	# Table linking
	order = relationship('Order', back_populates='items')
	# Serialization
	@property
	def serialize(self):
		return {
    		'id': self.id,
    		'amount': self.amount,
    		'name': self.name
    	}

class Offer(Base):
	# Table name
	__tablename__ = 'offers'
	# Table attributes
	id = Column(Integer, Sequence('offer_id_seq'), primary_key=True)
	price = Column(String(25))
	time = Column(String(25))
	# Table relations
	order_id = Column(Integer, ForeignKey('orders.id'))
	store_id = Column(Integer, ForeignKey('stores.id'))
	# Table linking
	order = relationship('Order', back_populates='offers')
	store = relationship('Store', back_populates='offers')
	# Serialization
	@property
	def serialize(self):
		return {
			'id': self.id,
			'price': self.price,
			'time': self.time,
			'order_id': self.order_id,
			'store_id': self.store_id,
			'stars': self.store.stars
		}

class Order(Base):
	# Table name
	__tablename__ = 'orders'
	# Table attributes
	id = Column(Integer, Sequence('order_id_seq'), primary_key=True)
	place = Column(String(100))
	status = Column(Integer)
	price = Column(String(25))
	time = Column(String(25))
	lat = Column(Numeric)
	lon = Column(Numeric)
	user_id = Column(String(50))
	created_at = Column(DateTime)
	# Table relations
	store_id = Column(Integer, ForeignKey('stores.id'))
	# Table linking
	store = relationship('Store', back_populates='orders')
	items = relationship('Item', back_populates='order')
	rating = relationship('Rating', back_populates='order', uselist=False)
	offers = relationship('Offer', back_populates='order')
	# Serialization
	@property
	def serialize(self):
		return {
    		'id': self.id,
    		'place': self.place,
    		'status': ORDER_STATUS_MESSAGES[self.status],
    		'price': self.price,
    		'time': self.time,
    		'geoplace': {
    			'lat': str(self.lat),
    			'lon': str(self.lon)
    		},
    		'user_id': self.user_id,
    		'store_id': self.store_id,
    		'items': [item.serialize for item in self.items],
    		'rating': self.rating.serialize if self.rating else {},
    		'created_at': self.created_at
    	}

class Rating(Base):
	# Table name
	__tablename__ = 'ratings'
	# Table attributes
	id = Column(Integer, Sequence('rating_id_seq'), primary_key=True)
	stars = Column(Integer)
	comment = Column(String(200))
	# Table relations
	order_id = Column(Integer, ForeignKey('orders.id'))
	# Table linking
	order = relationship('Order', back_populates='rating')
	# Serialization
	@property
	def serialize(self):
		return {
    		'id': self.id,
    		'stars': self.stars,
    		'comment': self.comment
    	}

class Store(Base):
	# Table name
	__tablename__ = 'stores'
	# Table attributes
	id = Column(Integer, Sequence('store_id_seq'), primary_key=True)
	name = Column(String(100))
	place = Column(String(100))
	stars = Column(Integer)
	lat = Column(Numeric)
	lon = Column(Numeric)
	rad = Column(Integer)
	user_id = Column(String(50), unique=True, nullable=False)
	created_at = Column(DateTime)
	# Table linking
	offers = relationship('Offer', back_populates='store')
	orders = relationship('Order', back_populates='store')
	# Serialization
	@property
	def serialize(self):
		return {
    		'id': self.id,
    		'name': self.name,
    		'place': self.place,
    		'stars': self.stars,
    		'geoplace': {
    			'lat': float(self.lat),
    			'lon': float(self.lon)
    		},
    		'created_at': self.created_at,
    		'user_id': self.user_id
    	}

# Create tables
Base.metadata.create_all(engine)
session.commit()

# ###############################################
# ############### Error handling ################
# ###############################################

@app.errorhandler(400)
def bad_request(error):
	return make_response(jsonify({ 'error': 'bad request' }), 400)

@app.errorhandler(401)
def unauthorized(error):
	return make_response(jsonify({ 'error': 'unauthorized' }), 401)

@app.errorhandler(404)
def not_found(error):
	return make_response(jsonify({ 'error': 'not found' }), 404)

@app.errorhandler(405)
def bad_method(error):
	return make_response(jsonify({ 'error': 'method not allowed' }), 405)

@app.errorhandler(409)
def conflict(error):
	return make_response(jsonify({ 'error': 'conflict resource' }), 409)

@app.errorhandler(500)
def unknown(error):
	return make_response(jsonify({ 'error': 'unknown error, try again later' }), 500)

@app.teardown_request
def teardown_request(exception):
	if exception:
		session.rollback()

# ###############################################
# ################ Authorization ################
# ###############################################

def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.headers.get('Authorization', None)
		if not auth:
			abort(401)
		
		parts = auth.split()
		if parts[0].lower() != 'bearer':
			abort(400)
		if len(parts) == 1:
			abort(400)
		if len(parts) > 2:
			abort(400)

		token = parts[1]
		try:
			payload = jwt.decode(
				token,
				base64.b64decode(client_secret.replace('_','/').replace('-','+')),
				audience=client_id
			)
		except Exception:
			abort(401)

		_request_ctx_stack.top.current_user = user = payload
		return f(*args, **kwargs)
	return decorated

# ###############################################
# ############ No role API functions ############
# ###############################################

@app.route('/', methods=['GET'])
@requires_auth
def index():
	"""
	Test the API is live by returning the token
	decoded body, steps to proceed are:
		1. Returns the token decoded body.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	return jsonify(user), 200

def get_orders(status):
	"""
	Retrieve all the existing orders as a user or as
	a store, steps to proceed are:
		1. Search all orders using the given user and status.
		2. Returns every order found.
	"""
	# Step 1
	orders = []
	user = _request_ctx_stack.top.current_user
	user_id = user['sub'].split('|')[1]
	if user['app_metadata']['user_role'] == 'user':
		orders = session.query(Order).filter(and_(Order.user_id == user_id, Order.status == status)).order_by(desc(Order.created_at)).all()
	elif user['app_metadata']['user_role'] == 'store':
		orders = session.query(Order).join(Store).filter(and_(Store.user_id == user_id, Order.status == status)).order_by(desc(Order.created_at)).all()
	# Step 2
	return jsonify(json_list=[order.serialize for order in orders]), 200

@app.route('/api/v1.0/order/accepted', methods=['GET'])
@requires_auth
def get_accepted_orders():
	return get_orders(ORDER_ACCEPTED)

@app.route('/api/v1.0/order/finished', methods=['GET'])
@requires_auth
def get_finished_orders():
	return get_orders(ORDER_FINISHED)

@app.route('/api/v1.0/order/<int:order_id>', methods=['GET'])
@requires_auth
def get_order(order_id):
	"""
	Retrieve an specific order with a given id as a
	user or as a store, steps to proceed are:
		1. Search the order with the given id and user.
		2. Returns the order if there is one.
	"""
	# Step 1
	order = None
	user = _request_ctx_stack.top.current_user
	user_id = user['sub'].split('|')[1]
	if user['app_metadata']['user_role'] == 'user':
		order = session.query(Order).filter(and_(Order.id == order_id, Order.user_id == user_id)).first()
	elif user['app_metadata']['user_role'] == 'store':
		order = session.query(Order).join(Store).filter(and_(Order.id == order_id, Store.user_id == user_id)).first()
	if not order:
		abort(404)
	# Step 2
	return jsonify(order.serialize), 200

# ###############################################
# ########### User role API functions ###########
# ###############################################

@app.route('/api/v1.0/order', methods=['POST'])
@requires_auth
def create_order():
	"""
	Make a new order as a user, steps to proceed are:
		1. Check user's role is "user".
		2. Check request data exists and is valid.
		3. Check accepted orders limit is still valid.
		4. Create the new order using provided data.
		5. Create every order item.
		6. Returns the just created order.
	"""
	# Step 1
	print 'STEP_1'
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'user':
		abort(401)
	# Step 2
	print 'STEP_2'
	if not request.json or not valid_create_order(request.json):
		abort(400)
	# Step 3
	print 'STEP_3'
	user_id = user['sub'].split('|')[1]
	orders = session.query(Order).filter(and_(Order.user_id == user_id, Order.status != ORDER_FINISHED)).all()
	accepted_orders = [order for order in orders if order.status == ORDER_ACCEPTED]
	made_order = [order for order in orders if order.status == ORDER_MADE]
	if len(accepted_orders) >= USER_ORDER_LIMIT:
		abort(400)
	if len(made_order) > 0:
		abort(400)
	# Step 4
	print 'STEP_4'
	order = Order(
		place=request.json['place'],
		status=ORDER_MADE,
		lat=request.json['geoplace']['lat'],
		lon=request.json['geoplace']['lon'],
		user_id=user_id,
		created_at=datetime.now()
	)
	session.add(order)
	session.flush()
	# Step 5
	print 'STEP_5'
	items = []
	for val in request.json['items']:
		item = Item(
			amount=val['amount'],
			name=val['name'],
			order_id=order.id
		)
		items.append(item)
	session.add_all(items)
	session.commit()
	# Step 6
	print 'STEP_6'
	return jsonify(order.serialize), 201

@app.route('/api/v1.0/order/<int:order_id>', methods=['PUT'])
@requires_auth
def accept_offer(order_id):
	"""
	Accept a store's offer as a user, steps to proceed are:
		1. Check user's role is "user".
		2. Check request data exists and is valid.
		3. Retrieve and check the offer with the given id.
		4. Retrieve and check the order with the given id.
		5. Modify and save the just retrieved order.
		6. Retrieve and delete other offers.
		7. Returns the just accepted order.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'user':
		abort(401)
	# Step 2
	if not request.json or not valid_accept_offer(request.json):
		abort(400)
	# Step 3
	offer = session.query(Offer).filter(and_(Offer.id == request.json['offer_id'], Offer.order_id == order_id)).first()
	if not offer:
		abort(404)
	# Step 4
	user_id = user['sub'].split('|')[1]
	order = session.query(Order).filter(and_(Order.id == order_id, Order.user_id == user_id)).first()
	if not order:
		abort(404)
	if order.status != ORDER_MADE:
		abort(400)
	# Step 5
	order.status = ORDER_ACCEPTED
	order.price = offer.price
	order.time = offer.time
	order.store_id = offer.store_id
	session.add(order)
	# Step 6
	offers = session.query(Offer).filter(Offer.order_id == order.id)
	for offer in offers:
		session.delete(offer)
	session.commit()
	# Step 7
	return jsonify(order.serialize), 200

@app.route('/api/v1.0/order/<int:order_id>', methods=['DELETE'])
@requires_auth
def delete_order(order_id):
	"""
	Cancel (delete) an existing order as a user, steps
	to proceed are:
		1. Check user's role is "user".
		2. Search the order using the given id and user.
		3. Delete the just retrieved order.
		4. Returns an OK message and status.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'user':
		abort(401)
	# Step 2
	user_id = user['sub'].split('|')[1]
	order = session.query(Order).filter(and_(Order.id == order_id, Order.user_id == user_id)).first()
	if not order:
		abort(404)
	if order.status == ORDER_FINISHED:
		abort(400)
	# Step 3
	session.delete(order)
	session.commit()
	# Step 4
	return jsonify({ 'msg': 'success' }), 200

@app.route('/api/v1.0/rating', methods=['POST'])
@requires_auth
def rate_order():
	"""
	Create a new rating for a given order as a
	user, steps to proceed are:
		1. Check user's role is "user".
		2. Check request data exists and is valid.
		3. Search the order with the given id and user.
		4. Create a new rating with the given data.
		5. Update store's rating.
		6. Change order's status to rated.
		7. Returns the just created rating.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'user':
		abort(401)
	# Step 2
	if not request.json or not valid_rate_order(request.json):
		abort(400)
	# Step 3
	user_id = user['sub'].split('|')[1]
	order_id = request.json['order_id']
	order = session.query(Order).filter(and_(Order.id == order_id, Order.user_id == user_id)).first()
	if not order:
		abort(404)
	if order.status != ORDER_ACCEPTED:
		abort(400)
	# Step 4
	rating = Rating(
		stars=request.json['stars'],
		comment=request.json['comment'],
		order_id=order_id
	)
	session.add(rating)
	# Step 5
	store_id = order.store_id
	store = session.query(Store).filter(Store.id == store_id).first()
	orders = session.query(Order).filter(and_(Order.store_id == store_id, Order.status == ORDER_FINISHED)).count()
	store.stars = (store.stars * orders + rating.stars) / (orders + 1)
	session.add(store)
	# Step 6
	order.status = ORDER_FINISHED
	session.add(order);
	session.commit()
	# Step 7
	return jsonify(rating.serialize), 201

# ###############################################
# ########## Store role API functions ###########
# ###############################################

@app.route('/api/v1.0/store/<int:store_id>/order/nearme', methods=['GET'])
@requires_auth
def get_nearme_orders(store_id):
	"""
	Retrieve all the existing orders as a user or as
	a store, steps to proceed are:
		1. Check user's role is "store".
		2. Retrieve and check the store with the given id.
		3. Search all near orders using the store's location.
		4. Returns every order found.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'store':
		abort(401)
	# Step 2
	store = session.query(Store).filter(Store.id == store_id).first()
	if not store:
		abort(404)
	# Step 3
	radius = store.rad or DEFAULT_ORDER_RADIUS
	distance = KM_UNIT *\
			   func.acos(func.cos(func.radians(store.lat)) *\
			   func.cos(func.radians(Order.lat)) *\
			   func.cos(func.radians(Order.lon) -\
			   func.radians(store.lon)) +\
			   func.sin(func.radians(store.lat)) *\
			   func.sin(func.radians(Order.lat)))
	orders = session.query(Order).filter(and_(distance <= radius, Order.status == ORDER_MADE)).order_by(desc(Order.created_at)).all()
	# Step 4
	return jsonify(json_list=[order.serialize for order in orders]), 200

@app.route('/api/v1.0/offer', methods=['POST'])
@requires_auth
def create_offer():
	"""
	Make a new offer as a store, steps to proceed are:
		1. Check user's role is "store".
		2. Check request data exists and is valid.
		3. Retrieve and check the offer with the given id.
		4. Retrieve and check the store with the given id.
		5. Check accepted orders limit is still valid.
		6. Check order's offers limit is still valid.
		7. Check store has not made an offer already.
		8. Create the new offer using provided data.
		9. Returns the just created order.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'store':
		abort(401)
	# Step 2
	if not request.json or not valid_create_offer(request.json):
		abort(400)
	# Step 3
	order_id = request.json['order_id']
	order = session.query(Order).filter(Order.id == order_id).first()
	if not order:
		abort(404)
	if order.status != ORDER_MADE:
		abort(400)
	# Step 4
	store_id = request.json['store_id']
	store = session.query(Order).filter(Store.id == store_id).first()
	if not store:
		abort(404)
	# Step 5
	user_id = user['sub'].split('|')[1]
	orders = session.query(Order).join(Store).filter(and_(Store.user_id == user_id, Order.status == ORDER_ACCEPTED)).all()
	if len(orders) >= STORE_ORDER_LIMIT:
		abort(400)
	# Step 6
	offers = session.query(Offer).filter(Offer.order_id == order_id).all()
	if len(offers) >= OFFER_ORDER_LIMIT:
		abort(400)
	# Step 7
	offer = session.query(Offer).filter(Offer.store_id == store_id).first()
	if offer:
		abort(400)
	# Step 8
	offer = Offer(
		price=request.json['price'],
		time=request.json['time'],
		order_id=request.json['order_id'],
		store_id=request.json['store_id']
	)
	session.add(offer)
	session.commit()
	# Step 9
	return jsonify(offer.serialize), 201

# ###############################################
# ########### Verification functions ############
# ###############################################

def valid_create_order(data):
	"""
	Verifies that the given data match correctly
	with the following structure:
		{
			"place": String,
			"geoplace": {
				"lat": String,
				"lon": String
			},
			"items": [
				{
					"amount": Integer,
					"name": String
				},
				...
			]
		}
	"""
	# Verify place
	print 'place'
	if 'place' not in data or type(data['place']) is not unicode or not data['place']:
		return False
	# Verify geoplace outside
	print 'geoplace'
	if 'geoplace' not in data or type(data['geoplace']) is not dict:
		return False
	# Verify geoplace inside
	print 'lat'
	if 'lat' not in data['geoplace'] or type(data['geoplace']['lat']) is not float:
		return False
	print 'lon'
	if 'lon' not in data['geoplace'] or type(data['geoplace']['lon']) is not float:
		return False
	# Verify items outside
	print 'items'
	if 'items' not in data or type(data['items']) is not list:
		return False
	if len(data['items']) < 1:
		return False
	# Verify items inside
	print 'inside'
	for item in data['items']:
		if 'amount' not in item or type(item['amount']) is not int:
			return False
		if item['amount'] < 1:
			return False
		if 'name' not in item or type(item['name']) is not unicode or not item['name']:
			return False
	return True

def valid_accept_offer(data):
	"""
	Verifies that the given data match correctly
	with the following structure:
		{
			"offer_id": FK
		}
	"""
	if 'offer_id' not in data:
		return False
	return True

def valid_rate_order(data):
	"""
	Verifies that the given data match correctly
	with the following structure:
		{
			"stars": Integer,
			"comment": String,
			"order_id": FK
		}
	"""
	if 'stars' not in data or type(data['stars']) is not int or data['stars'] < 1 or data['stars'] > 10:
		return False
	if 'comment' not in data or type(data['comment']) is not unicode or (data['stars'] < 4 and not data['comment']):
		return False
	if 'order_id' not in data:
		return False
	return True

def valid_create_offer(data):
	"""
	Verifies that the given data match correctly
	with the following structure:
		{
			"price": String,
			"time": String,
			"order_id": FK,
			"store_id": FK
		}
	"""
	if 'price' not in data or type(data['price']) is not unicode or not data['price']:
		return False
	if 'time' not in data or type(data['time']) is not unicode or not data['time']:
		return False
	if 'order_id' not in data:
		return False
	if 'store_id' not in data:
		return False
	return True

# ###############################################
# ################ Run functions ################
# ###############################################

if __name__ == '__main__':
	app.run(debug=True)
