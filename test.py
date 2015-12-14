from app import Base, engine, Session, Store, Order

session = Session()
stores = session.query(Store).all()
print stores