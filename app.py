from flask import Flask,redirect,url_for,request,render_template,flash,session
import mysql.connector
from flask_session import Session
from key import secret_key,salt
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from cmail import sendmail
import os
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
host=os.environ.get('RDS_HOSTNAME')
port=os.environ.get('RDS_PORT')
with mysql.connector.connect(host=host,user=user,password=password,port=port,db=db) as conn:
    cursor=conn.cursor(buffered=True)
    cursor.execute("create table if not exists(username varchar(50) primary key,password varchar(15),email varchar(60) unique)")
    cursor.execute("create table if not exists(nid int not null auto_increment primary key,title tinytext,content text,date timestamp default now() on update now(),added_by varchar(50),foreign key(added_by) references users(username))")
    cursor.close()
    mydb=mysql.connector.connect(host=host,user=user,password=password,db=db)
#mydb=mysql.connector.connect(host="localhost",user="root",password="admin",db="pnm")
@app.route('/')
def index():
    return render_template('title.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s and password=%s',[username,password])
        count=cursor.fetchone()[0]
        if count==1:
            session['user']=username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/homepage')
def home():
    if session.get('user'):
        return render_template('homepage.html')
    else:
        return redirect(url_for('login'))
@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*)  from users where username=%s',[username])
        count=cursor.fetchone()[0]
        cursor.execute('select count(*)  from users where email=%s',[email])
        count1=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            flash('username is already in use')
            return render_template('registration.html')
        elif count1==1:
            flash('Email already in use')
            return render_template('registration.html')
        data={'username':username,'password':password,'email':email}
        subject='Email Confirmation'
        body=f"Thanks for signing up\n\n follow this link  further steps-{url_for('confirm',token=token(data),_external=True)}"
        sendmail(to=email,subject=subject,body=body)
        flash('Confirmation link sent to mail')
        return redirect(url_for('login'))
    return render_template('registration.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:
        #print(e)
        return 'Link Expired register again'
    else:
        cursor=mydb.cursor(buffered=True)
        username=data['username']
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.close()
            flash('you already registered')
            return redirect(url_for('login'))
        else:
            cursor.execute('insert into users values(%s,%s,%s)',[data['username'],data['password'],data['email']])
            mydb.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('login'))
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        flash('Successfully loged out')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            content=request.form['content']
            username=session.get('user')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into notes (title,content,added_by) values(%s,%s,%s)',[title,content,username])
            mydb.commit()
            cursor.close()
            flash('Notes added successfully')
            return redirect(url_for('allnotes'))
        return render_template('addnotes.html')
    else:
        return redirect(url_for('login'))
@app.route('/allnotes')
def allnotes():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select nid,title,date from notes where added_by=%s order by date desc',[username])
        data=cursor.fetchall()
        print(data)
        cursor.close()
        return render_template('table.html',data=data)
    else:
        return redirect(url_for('login'))
@app.route('/viewnotes/<nid>')
def viewnotes(nid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select title,content from notes where nid=%s',[nid])
        data=cursor.fetchone()
        cursor.close()
        title=data[0]
        content=data[1]
        return render_template('view.html',title=title,content=content)
    else:
        return redirect(url_for('login'))
@app.route('/delete/<nid>')
def delete(nid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from notes where nid=%s',[nid])
        cursor.close()
        flash('Notes deleted')
        return redirect(url_for('allnotes'))
    else:
        return redirect(url_for('login'))
@app.route('/updatenotes/<nid>',methods=['GET','POST'])
def updatenotes(nid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select title,content from notes where nid=%s',[nid])
        data=cursor.fetchone()
        cursor.close()
        title=data[0]
        content=data[1]
        if request.method=='POST':
            title=request.form['title']
            content=request.form['content']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update notes set title=%s,content=%s where nid=%s',[title,content,nid])
            mydb.commit()
            flash('Notes updated successfully')
            return redirect(url_for('allnotes'))
        return render_template('update.html',title=title,content=content)
    else:
        return redirect(url_for('login'))
if __name__=='__main__':
    app.run()