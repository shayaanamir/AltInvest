// Runs once, when the production MongoDB volume is first created (docker-compose.prod.yml mounts this folder
// at /docker-entrypoint-initdb.d). Creates the application's own user with readWrite on the application
// database only; the root user from MONGO_INITDB_ROOT_* is kept for administration and never given to the app.
//
// It does not run again on an existing volume. To change the app password later:
//   docker compose -f docker-compose.prod.yml --env-file .env.prod exec mongodb \
//     mongosh -u "$MONGO_ROOT_USER" -p --authenticationDatabase admin \
//     --eval 'db.getSiblingDB("aaip_db").changeUserPassword("altinvest", "<new password>")'
// then update MONGO_APP_PASSWORD in .env.prod and recreate the backend.

const dbName = process.env.MONGO_APP_DB;
const user = process.env.MONGO_APP_USER;
const pwd = process.env.MONGO_APP_PASSWORD;

if (!dbName || !user || !pwd) {
  throw new Error("MONGO_APP_DB, MONGO_APP_USER and MONGO_APP_PASSWORD must all be set");
}

db.getSiblingDB(dbName).createUser({
  user: user,
  pwd: pwd,
  roles: [{ role: "readWrite", db: dbName }],
});
print(`[mongo-init] created user ${user} with readWrite on ${dbName}`);
