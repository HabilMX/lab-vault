# Pide a Vault un usuario temporal de PostgreSQL, lee los clientes
# y descifra cada CURP con Transit. La app no guarda ninguna contraseña.
import base64, json, os, urllib.request
import psycopg

VAULT = os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
TOKEN = os.environ["VAULT_TOKEN"]  # te lo da quien opera Vault; nunca va en el código

def vault(ruta, datos=None):
    cuerpo = json.dumps(datos).encode() if datos else None
    req = urllib.request.Request(f"{VAULT}/v1/{ruta}", data=cuerpo,
                                 headers={"X-Vault-Token": TOKEN})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["data"]

cred = vault("database/creds/lector")
print("Vault me prestó el usuario", cred["username"])

with psycopg.connect(host="127.0.0.1", port=os.environ.get("PGPORT", "5432"),
                     dbname="tienda", user=cred["username"],
                     password=cred["password"]) as conexion:
    for nombre, curp in conexion.execute("SELECT nombre, curp FROM clientes"):
        claro = vault("transit/decrypt/curp", {"ciphertext": curp})["plaintext"]
        print(f"{nombre:6} {curp[:12]}...  ->  {base64.b64decode(claro).decode()}")
