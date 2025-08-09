import pymysql
conn = pymysql.connect(
    host='gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
    port=4000,
    user='',
    password='',
    database='test',
    ssl_ca=r"C:\Users\nidhi\OneDrive\Documents\projs\ihita_app\isrgrootx1.pem.txt",
    ssl_verify_cert=True
)
print("Connected successfully!")
conn.close()
