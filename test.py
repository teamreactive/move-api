#!flask/bin/python
import requests

from app import Base, engine, session, Store
from datetime import datetime

BASE_URL = 'http://localhost:5000'

def headers(profile):
	token = {
		'user': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhcHBfbWV0YWRhdGEiOnsidXNlcl9yb2xlIjoidXNlciJ9LCJpc3MiOiJodHRwczovL21vdmVhcHAuYXV0aDAuY29tLyIsInN1YiI6ImF1dGgwfDU2NmM3YTEyMzYxMTIyNzQ0NzhkOTg5YiIsImF1ZCI6Ilk3UzhPV2pFamI5OUlEVWdKYWRpcDhEaU9kam5JSTVlIiwiZXhwIjoxNDUwNDA2NDczLCJpYXQiOjE0NTAzNzA0NzN9.98Uibh5ggNGh_J8k6GW3-vmRddhRE_4MEeJOc1XW1Wc',
		'store': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhcHBfbWV0YWRhdGEiOnsidXNlcl9yb2xlIjoic3RvcmUifSwiaXNzIjoiaHR0cHM6Ly9tb3ZlYXBwLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1NjZlYTQ0MDgyZTU3YWJlN2Q4NGI5OWMiLCJhdWQiOiJZN1M4T1dqRWpiOTlJRFVnSmFkaXA4RGlPZGpuSUk1ZSIsImV4cCI6MTQ1MDQwNjUwNSwiaWF0IjoxNDUwMzcwNTA1fQ.v8R77zwqZ1xKkYa5jNO3mCI82PeRPswTVuSQjvyIzV8'
	}
	return {
		'Content-Type': 'application/json',
		'Authorization': 'Bearer %s' % token[profile]
	}

session.commit()
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
store = Store(
	name='Cigarreria Don Pedro',
	place='Calle 160 #14 07',
	stars=10,
	lat=10.4392,
	lon=10.4392,
	rad=1,
	user_id='566ea44082e57abe7d84b99c',
	created_at=datetime.now()
)
session.add(store)
session.commit()

print ''
print '#' * 70
print '#' * 25 + ' INITIALIZING TESTS ' + '#' * 25
print '#' * 70
print ''

print 'GET /'
url = BASE_URL + '/'
r = requests.get(url, headers=headers('user'))
print r.status_code
print r.text

print '\n'

print 'GET /'
url = BASE_URL + '/'
r = requests.get(url, headers=headers('store'))
print r.status_code
print r.text

print '\n'

print 'GET /api/v1.0/order/accepted'
url = BASE_URL + '/api/v1.0/order/accepted'
r = requests.get(url, headers=headers('user'))
print r.status_code
print r.text

print '\n'

print 'GET /api/v1.0/order/finished'
url = BASE_URL + '/api/v1.0/order/finished'
r = requests.get(url, headers=headers('user'))
print r.status_code
print r.text

print '\n'

print 'POST /api/v1.0/order'
url = BASE_URL + '/api/v1.0/order'
data = {
	'place': 'Calle 165b #15b 06 Prados de San Martin 1-1502',
	'geoplace': {
		'lat': 10.4392,
		'lon': 10.4392
	},
	'items': [
		{
			'amount': 4,
			'name': 'Coca Cola 500ml'
		},
		{
			'amount': 2,
			'name': 'Ponque gala vainilla'
		}
	]
}
r = requests.post(url, headers=headers('user'), json=data)
print r.status_code
print r.text

print '\n'

print 'GET /api/v1.0/order/<int:order_id>'
id = 1
url = BASE_URL + '/api/v1.0/order/%d' % id
r = requests.get(url, headers=headers('user'))
print r.status_code
print r.text

print '\n'

print 'POST /api/v1.0/offer'
url = BASE_URL + '/api/v1.0/offer'
data = {
	'price': '10000',
	'time': '1hora',
	'order_id': 1,
	'store_id': 1
}
r = requests.post(url, headers=headers('store'), json=data)
print r.status_code
print r.text

print '\n'

print 'PUT /api/v1.0/order/<int:order_id>'
id = 1
url = BASE_URL + '/api/v1.0/order/%d' % id
data = {
	'offer_id': 1
}
r = requests.put(url, headers=headers('user'), json=data)
print r.status_code
print r.text

print '\n'

print 'POST /api/v1.0/rating'
url = BASE_URL + '/api/v1.0/rating'
data = {
	'stars': 2,
	'comment': 'El servicio se demoro mucho',
	'order_id': '1'
}
r = requests.post(url, headers=headers('user'), json=data)
print r.status_code
print r.text

print '\n'

print 'GET /api/v1.0/order/<int:order_id>'
id = 1
url = BASE_URL + '/api/v1.0/order/%d' % id
r = requests.get(url, headers=headers('user'))
print r.status_code
print r.text

print '\n'

print 'POST /api/v1.0/order'
url = BASE_URL + '/api/v1.0/order'
data = {
	'place': 'Calle 165b #15b 06 Prados de San Martin 1-1502',
	'geoplace': {
		'lat': 10.4392,
		'lon': 10.4392
	},
	'items': [
		{
			'amount': 4,
			'name': 'Coca Cola 500ml'
		},
		{
			'amount': 2,
			'name': 'Ponque gala vainilla'
		}
	]
}
r = requests.post(url, headers=headers('user'), json=data)
print r.status_code
print r.text

print '\n'

print 'GET /api/v1.0/store/<int:store_id>/order/nearme'
id = 1
url = BASE_URL + '/api/v1.0/store/%d/order/nearme' % id
r = requests.get(url, headers=headers('store'))
print r.status_code
print r.text

print '\n'

print 'DELETE /api/v1.0/order/<int:order_id>'
id = 2
url = BASE_URL + '/api/v1.0/order/%d' % id
r = requests.delete(url, headers=headers('user'))
print r.status_code
print r.text

print '\n'

print 'GET /api/v1.0/order/<int:order_id>'
id = 2
url = BASE_URL + '/api/v1.0/order/%d' % id
r = requests.get(url, headers=headers('user'))
print r.status_code
print r.text

print ''
print '#' * 70
print '#' * 25 + '    END OF TESTS    ' + '#' * 25
print '#' * 70
print ''
