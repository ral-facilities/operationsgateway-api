db = db.getSiblingDB('mongo');  // create to the 'mongo' database

db.createUser({
  user: "tester",
  pwd: "tester",
  roles: [
    { role: "readWrite", db: "mongo" },  // Allow read and write access to the 'mongo' database
    { role: "dbAdmin", db: "mongo" }     // Allow administrative actions on the 'mongo' database
  ]
});