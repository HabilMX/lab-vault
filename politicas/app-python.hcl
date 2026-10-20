# La app de Python puede pedir usuarios temporales de solo lectura
# y descifrar CURPs. No puede cifrar, rotar ni leer otros secretos.
path "database/creds/lector" {
  capabilities = ["read"]
}
path "transit/decrypt/curp" {
  capabilities = ["update"]
}
