curl -L 'http://localhost:8081/connect' \
-H 'Content-Type: application/json' \
-d '{
    "hostname": "process2:8082"
}'

curl -L 'http://localhost:8082/connect' \
-H 'Content-Type: application/json' \
-d '{
    "hostname": "process:8081"
}'

curl -L 'http://localhost:8081/update' \
-H 'Content-Type: application/json' \
-d '{
    "camera": true,
    "microphone": true,
    "background": 2
}'
curl -L 'http://localhost:8082/update' \
-H 'Content-Type: application/json' \
-d '{
    "camera": true,
    "microphone": false,
    "background": 1
}'

curl -L 'http://localhost:8081/send' \
-H 'Content-Type: application/json' \
-d '{

    "message":"Message"
}'