import pymysql
conn = pymysql.connect(
    host='gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
    port=4000,
    user='3v5cUKca8NJCP7r.root',
    password='I6l7xbsgvFbsqUYZ',
    database='test',
    ssl_ca=r"C:\Users\nidhi\OneDrive\Documents\projs\ihita_app\isrgrootx1.pem.txt",
    ssl_verify_cert=True
)
print("Connected successfully!")
conn.close()