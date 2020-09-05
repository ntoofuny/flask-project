from models import User

#query = User.delete().where(User.id ==3)
query.execute()
users = User.select()

for user in users:
  print(str(user.id) + " " + str(user.username))
  
#http://jonathansoma.com/tutorials/webapps/intro-to-peewee/