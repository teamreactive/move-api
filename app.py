#!flask/bin/python
import base64
import jwt
import os

from dotenv import Dotenv
from flask import abort, Flask, jsonify, make_response, request, _request_ctx_stack, url_for
from flask.ext.cors import cross_origin
from functools import wraps
from werkzeug.local import LocalProxy

# ###############################################
# ############### Initial config ################
# ###############################################

env = None
try:
	env = Dotenv('./.env')
	client_id = env["AUTH0_CLIENT_ID"]
	client_secret = env["AUTH0_CLIENT_SECRET"]
except IOError:
	env = os.environ

app = Flask(__name__)
# Authentication annotation
current_user = LocalProxy(lambda: _request_ctx_stack.top.current_user)

# ###############################################
# ################## Constants ##################
# ###############################################

ORDER_MADE = 0
ORDER_ACCEPTED = 1
ORDER_FINISHED = 2

# ###############################################
# ################## Fake data ##################
# ###############################################

users = [
	{
		'id': 1,
		'name': 'Juan Camilo Bages',
		'email': 'jcbages@outlook.com',
		'phone': '+573003244592',
		'password': '123',
		'orders': []
	}
]

orders = []

stores = [
	{
		'id': 1,
		'name': 'Cigarreria Hector',
		'place': 'Calle 8 13 23',
		'stars': 7,
		'email': 'cighector@gmail.com',
		'password': 'abc'
	}
]

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
# ################ API functions ################
# ###############################################

@app.route('/', methods=['GET'])
def index():
	return jsonify({ 'msg': 'we are live' }), 200

@app.route('/api/v1.0/user/signin', methods=['POST'])
def signin():
	if not request.json or not valid_signin(request.json):
		abort(400)
	user = [user for user in users if user['email'] == request.json['email']]
	if len(user) == 0:
		abort(404)
	if user[0]['password'] != request.json['password']:
		abort(404)
	return jsonify({ 'token': 'heyimatoken' }), 200

@app.route('/api/v1.0/user/signup', methods=['POST'])
def signup():
	if not request.json or not valid_signup(request.json):
		abort(400)
	user = [user for user in users if user['email'] == request.json['email']]
	if len(user) != 0:
		abort(409)
	user = {
		'id': 1 if len(users) == 0 else users[-1]['id'] + 1,
		'name': request.json['name'],
		'email': request.json['email'],
		'phone': request.json['phone'],
		'password': request.json['password'],
		'orders': []
	}
	users.append(user)
	return jsonify({ 'token': 'heyimatoken' }), 201

@app.route('/api/v1.0/user/signout', methods=['POST'])
# @requires_auth
def signout():
	return jsonify({ 'msg': 'success' }), 200

@app.route('/api/v1.0/user/<int:user_id>/order', methods=['POST'])
# @requires_auth
def create_order(user_id):
	if not request.json or not valid_create_order(request.json):
		abort(400)
	user = [user for user in users if user['id'] == user_id]
	if len(user) == 0:
		abort(404)
	order = {
		'id': 1 if len(orders) == 0 else orders[-1]['id'] + 1,
		'place': request.json['place'],
		'status': ORDER_MADE,
		'geoplace': request.json['geoplace'],
		'items': request.json['items']
	}
	orders.append(order)
	user[0]['orders'].append(order)
	return jsonify(order), 201

@app.route('/api/v1.0/user/<int:user_id>/order/<int:order_id>', methods=['PUT'])
# @requires_auth
def accept_offer(user_id, order_id):
	if not request.json or not valid_accept_offer(request.json):
		abort(400)
	user = [user for user in users if user['id'] == user_id]
	if len(user) == 0:
		abort(404)
	order = [order for order in user[0]['orders'] if order['id'] == order_id]
	if len(order) == 0:
		abort(404)
	store = [store for store in stores if store['id'] == request.json['store']]
	if len(store) == 0:
		abort(404)
	order[0]['status'] = ORDER_ACCEPTED
	order[0]['price'] = request.json['price']
	order[0]['time'] = request.json['time']
	order[0]['store'] = store[0]
	return jsonify(order[0]), 200

@app.route('/api/v1.0/user/<int:user_id>/order/<int:order_id>', methods=['DELETE'])
# @requires_auth
def delete_order(user_id, order_id):
	user = [user for user in users if user['id'] == user_id]
	if len(user) == 0:
		abort(404)
	order_user = [i for i in range(len(user[0]['orders'])) if user[0]['orders'][i]['id'] == order_id]
	order_whole = [i for i in range(len(orders)) if orders[i]['id'] == order_id]
	if len(order_user) == 0 or len(order_whole) == 0:
		abort(404)
	del user[0]['orders'][order_user[0]]
	del orders[order_whole[0]]
	return jsonify({ 'msg': 'success' }), 200

@app.route('/api/v1.0/user/<int:user_id>/order', methods=['GET'])
# @requires_auth
def get_orders(user_id):
	user = [user for user in users if user['id'] == user_id]
	if len(user) == 0:
		abort(404)
	return jsonify({ 'orders': user[0]['orders'], 'len': len(user[0]['orders']) }), 200

@app.route('/api/v1.0/user/<int:user_id>/order/<int:order_id>', methods=['GET'])
# @requires_auth
def get_order(user_id, order_id):
	user = [user for user in users if user['id'] == user_id]
	if len(users) == 0:
		abort(404)
	order = [order for order in user[0]['orders'] if order['id'] == order_id]
	if len(order) == 0:
		abort(404)
	return jsonify(order[0]), 200

@app.route('/api/v1.0/user/<int:user_id>', methods=['GET'])
# @requires_auth
def get_user(user_id):
	user = [user for user in users if user['id'] == user_id]
	if len(user) == 0:
		abort(404)
	return jsonify(user[0]), 200

@app.route('/api/v1.0/user/<int:user_id>', methods=['PUT'])
# @requires_auth
def update_user(user_id):
	if not request.json or not valid_update_user(request.json):
		abort(400)
	user = [user for user in users if user['id'] == user_id]
	if len(user) == 0:
		abort(404)
	user[0]['name'] = request.json.get('name', user[0]['name'])
	user[0]['email'] = request.json.get('email', user[0]['email'])
	user[0]['phone'] = request.json.get('phone', user[0]['phone'])
	return jsonify(user[0]), 200

@app.route('/api/v1.0/user/<int:user_id>/changepassword', methods=['PUT'])
# @requires_auth
def change_password(user_id):
	if not request.json or not valid_change_password(request.json):
		abort(400)
	user = [user for user in users if user['id'] == user_id]
	if len(user) == 0:
		abort(404)
	if user[0]['password'] != request.json['old_password']:
		abort(400)
	user[0]['password'] = request.json['new_password']
	return jsonify({ 'msg': 'success' }), 200

# ###############################################
# ########### Verification functions ############
# ###############################################

def valid_signin(data):
	"""
	{
		"email": <email>,
		"password": <password>
	}
	"""
	if 'email' not in data:
		return False
	if 'password' not in data:
		return False
	return True

def valid_signup(data):
	"""
	{
		"name": <name>,
		"email": <email>,
		"phone": <phone>,
		"password": <password>
	}
	"""
	if 'name' not in data:
		return False
	if 'email' not in data:
		return False
	if 'phone' not in data:
		return False
	if 'password' not in data:
		return False
	return True

def valid_create_order(data):
	"""
	{
		"place": <place>,
		"geoplace": {
			"lat": <lat>,
			"lon": <lon>
		},
		"items": [
			{
				"amount": <amount>,
				"name": <name>
			}
			...
		]
	}
	"""
	if 'place' not in data:
		return False
	if 'geoplace' not in data:
		return False
	if 'items' not in data:
		return False
	return True

def valid_accept_offer(data):
	"""
	{
		"price": <price>,
		"time": <time>,
		"store": <store>
	}
	"""
	if 'price' not in data:
		return False
	if 'time' not in data:
		return False
	if 'store' not in data:
		return False
	return True

def valid_update_user(data):
	"""
	{
		"name": <name>, OPTIONAL
		"email": <email>, OPTIONAL
		"phone": <phone> OPTIONAL
	}
	"""
	return True

def valid_change_password(data):
	"""
	{
		"old_password": <old_password>,
		"new_password": <new_password>
	}
	"""
	if 'old_password' not in data:
		return False
	if 'new_password' not in data:
		return False
	if data['old_password'] == data['new_password']:
		return False
	return True

# ###############################################
# ################ Run functions ################
# ###############################################

if __name__ == '__main__':
	app.run(debug=True)
