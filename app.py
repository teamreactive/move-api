#!flask/bin/python
import base64
import jwt
import os

from dotenv import Dotenv
from flask import abort, Flask, jsonify, make_response, request, _request_ctx_stack, url_for
from functools import wraps
from sqlalchemy import and_, Column, create_engine, ForeignKey, Integer, Sequence, String
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
	client_id = env["AUTH0_CLIENT_ID"]
	client_secret = env["AUTH0_CLIENT_SECRET"]
except IOError:
	env = os.environ
# Flask instance
app = Flask(__name__)
# Authentication annotation
current_user = LocalProxy(lambda: _request_ctx_stack.top.current_user)
# Database initialization
engine = create_engine('sqlite:///test.db', echo=True)
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

# ###############################################
# ################## DB Models ##################
# ###############################################

class Order(Base):
	# Table name
	__tablename__ = 'orders'
	# Table attributes
	id = Column(Integer, Sequence('order_id_seq'), primary_key=True)
	place = Column(String(100))
	status = Column(Integer)
	price = Column(String(25))
	time = Column(String(25))
	lat = Column(String(25))
	lon = Column(String(25))
	user_id = Column(String(50))
	# Table relations
	store_id = Column(Integer, ForeignKey('stores.id'))
	# Table linking
	store = relationship('Store', back_populates='orders')
	items = relationship('Item', back_populates='order')
	rating = relationship('Rating', back_populates='order', uselist=False)
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
    			'lat': self.lat,
    			'lon': self.lon
    		},
    		'user_id': self.user_id,
    		'store_id': self.store_id,
    		'items': [item.serialize for item in self.items],
    		'rating': self.rating.serialize if self.rating else {}
    	}

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

class Store(Base):
	# Table name
	__tablename__ = 'stores'
	# Table attributes
	id = Column(Integer, Sequence('store_id_seq'), primary_key=True)
	name = Column(String(100))
	place = Column(String(100))
	stars = Column(Integer)
	lat = Column(String(25))
	lon = Column(String(25))
	user_id = Column(String(50))
	# Table linking
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
    			'lat': self.lat,
    			'lon': self.lon
    		},
    		'user_id': self.user_id
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
    		'comment': self.comment,
    		'order_id': self.order_id
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
	return make_response(jsonify({ 'error': 'unknown error' }), 500)

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

@app.route('/api/v1.0/order', methods=['GET'])
@requires_auth
def get_orders():
	"""
	Retrieve all the existing orders as a user or as
	a store, steps to proceed are:
		1. Search all orders using the given user.
		2. Returns every order found.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	user_id = user['sub'].split('|')[1]
	orders = session.query(Order).filter(Order.user_id == user_id).all()
	# Step 2
	return jsonify(json_list=[order.serialize for order in orders]), 200

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
	user = _request_ctx_stack.top.current_user
	user_id = user['sub'].split('|')[1]
	order = session.query(Order).filter(and_(Order.id == order_id, Order.user_id == user_id)).first()
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
		3. Create the new order using provided data.
		4. Create every order item.
		5. Returns the just created order.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'user':
		abort(401)
	# Step 2
	if not request.json or not valid_create_order(request.json):
		abort(400)
	# Step 3
	user_id = user['sub'].split('|')[1]
	order = Order(
		place=request.json['place'],
		status=ORDER_MADE,
		lat=request.json['geoplace']['lat'],
		lon=request.json['geoplace']['lon'],
		user_id=user_id
	)
	session.add(order)
	session.commit()
	# Step 4
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
	# Step 5
	return jsonify(order.serialize), 201

@app.route('/api/v1.0/order/<int:order_id>', methods=['PUT'])
@requires_auth
def accept_offer(order_id):
	"""
	Accept a store's offer as a user, steps to proceed are:
		1. Check user's role is "user".
		2. Check request data exists and is valid.
		3. Verify that the store with the given id is real.
		4. Retrieve and check the order with the given id.
		5. Modify and save the just retrieved order.
		6. Returns the just accepted order.
	"""
	# Step 1
	user = _request_ctx_stack.top.current_user
	if user['app_metadata']['user_role'] != 'user':
		abort(401)
	# Step 2
	if not request.json or not valid_accept_offer(request.json):
		abort(400)
	# Step 3
	store = session.query(Store).filter(Store.id == request.json['store_id']).first()
	if not store:
		abort(404)
	# Step 4
	user_id = user['sub'].split('|')[1]
	order = session.query(Order).filter(and_(Order.id == order_id, Order.user_id == user_id)).first()
	if not order:
		abort(404)
	if order.status == ORDER_ACCEPTED:
		abort(400)
	# Step 5
	order.status = ORDER_ACCEPTED
	order.price = request.json['price']
	order.time = request.json['time']
	order.store_id = request.json['store_id']
	session.add(order)
	session.commit()
	# Step 6
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
		5. Change order's status to rated.
		6. Returns the just created rating.
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
	order.status = ORDER_FINISHED
	session.add(order);
	session.commit()
	# Step 6
	return jsonify(rating.serialize), 201

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
	if 'place' not in data or type(data['place']) is not unicode or not data['place']:
		return False
	# Verify geoplace outside
	if 'geoplace' not in data or type(data['geoplace']) is not dict:
		return False
	# Verify geoplace inside
	if 'lat' not in data['geoplace'] or type(data['geoplace']['lat']) is not unicode or not data['geoplace']['lat']:
		return False
	if 'lon' not in data['geoplace'] or type(data['geoplace']['lon']) is not unicode or not data['geoplace']['lon']:
		return False
	# Verify items outside
	if 'items' not in data or type(data['items']) is not list:
		return False
	if len(data['items']) < 1:
		return False
	# Verify items inside
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
			"price": String,
			"time": String,
			"store_id": FK
		}
	"""
	if 'price' not in data or type(data['price']) is not unicode or not data['price']:
		return False
	if 'time' not in data or type(data['time']) is not unicode or not data['time']:
		return False
	if 'store_id' not in data:
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

# ###############################################
# ################ Run functions ################
# ###############################################

if __name__ == '__main__':
	app.run(debug=True)
