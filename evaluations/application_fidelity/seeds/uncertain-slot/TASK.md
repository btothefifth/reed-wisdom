# Task

The launcher frees a slot when a response times out, so a replacement can start
while the original work might still exist. Fix this. Uncertain work must keep its
slot and current owner, accepted work must remain occupied, and proven creation
failure or observed completion must free only the matching slot. Leave successful
launches and the local tests working.
