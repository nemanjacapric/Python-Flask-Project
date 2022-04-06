from flask import Flask, render_template,redirect, url_for, request, session,flash
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import hashlib
import time
import os
import mysql.connector
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'januar2020'


UPLOAD_FOLDER = 'static/img'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
mydb = mysql.connector.connect(
	host="localhost",
	user="root",
	password="",
	database="oprema"
    )

@app.route('/register',methods=["POST","GET"])
def register():
	if request.method == "GET":
		return render_template("register.html")
	
	
	username = request.form['username']
	password = hashlib.sha256(request.form['password'].encode()).hexdigest() 
	usertype = request.form['usertype']
	mc = mydb.cursor()
	mc.execute(f"SELECT * FROM korisnici where username='{username}'")
	rez = mc.fetchall() 
	if len(rez) > 0:
		flash("Korisnik sa tim usernameom vec postoji")
		return redirect(url_for('register'))
	
	if 'file' not in request.files:
		return redirect(url_for('register'))
	file = request.files['file']
	
	if file.filename == '':
		flash("Niste uneli fajl")
		return render_template("register.html")
	
	if file:
		filename = request.form['username'] + ".jpg" 
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		putanja = f'./static/img/{filename}'
	
	mc = mydb.cursor()
	mc.execute(f"INSERT INTO korisnici VALUES(null, '{username}', '{password}', '{putanja}','{usertype}', 0 ) ")
	mydb.commit()
	
	return render_template('login.html')
@app.route('/login',methods=["POST","GET"])
def login():
	if request.method == "GET":
		return render_template('login.html')
	username = request.form['username']
	password = hashlib.sha256(request.form['password'].encode()).hexdigest()
	mc = mydb.cursor()
	mc.execute(f"SELECT * FROM korisnici where username='{username}'")
	rez = mc.fetchall()
	if len(rez) == 0:
		flash("Korisnik sa tim username ne postoji")
		return redirect(url_for('login'))
	if rez[0][2] != password:
		flash("Ne poklapaju se sifre")
		return redirect(url_for('login'))
	session['username'] = username
	session['usertype'] = rez[0][4]
	if rez[0][4] == "kupac": 
		return redirect(url_for('show_all'))
	else:
		
		mc = mydb.cursor()
		mc.execute(f"SELECT * FROM proizvodi WHERE seller_username='{username}'")
		rez = mc.fetchall()

		return redirect(url_for('profil',username=username))

@app.route('/show_all')
def show_all():
	if 'username' in session:
		mc = mydb.cursor()
		mc.execute(f"SELECT * FROM proizvodi")
		rez = mc.fetchall()
		
		return render_template("showall.html",proizvodi = rez,tip_korisnika = session['usertype'])
	return render_template("showall.html",proizvodi = rez)
@app.route('/dodaj_proizvod',methods=["POST", "GET"])
def dodaj_proizvod():
	username = session['username']
	naziv=request.form['naziv']
	opis = request.form['opis']
	cena = request.form['cena']	
	file = request.files['slika']

	if file:
		filename = username + "_" + naziv + ".jpg"
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		putanja = f'/static/img/{filename}'
		#return putanja
		
	mc = mydb.cursor()
	mc.execute(f"INSERT INTO proizvodi VALUES(null, '{username}', '{putanja}', '{opis}','{naziv}',{cena} ) ")
	mydb.commit()
	return redirect(url_for('profil',username=username))
	

@app.route('/profil/<username>')
def profil(username):
	
	mc = mydb.cursor()
	mc.execute(f"SELECT * FROM korisnici WHERE username='{username}'")
	korisnik = mc.fetchall()

	novac = korisnik[0][5]

	if len(korisnik) == 0:
		return "Ne postoji korisnik sa ovim imenom"
	if korisnik[0][4] == "prodavac":
		mc = mydb.cursor()
		mc.execute(f"SELECT * FROM proizvodi WHERE seller_username='{username}'")
		rez = mc.fetchall()

		return render_template("prodavac.html",proizvodi = rez)
	mc = mydb.cursor()
	mc.execute(f"SELECT * FROM korpa WHERE korisnik_username='{username}'")
	rez = mc.fetchall()
	proizvodi = []
	ukupna_cena =0
	
	for x in rez:
		mc = mydb.cursor()
		mc.execute(f"SELECT * FROM proizvodi WHERE id='{x[2]}'")
		p = mc.fetchall()
		proizvodi.append(p[0])
		ukupna_cena += int(p[0][5])
	
	return render_template("kupac.html",podaci =korisnik[0],proizvodi = proizvodi,ukupno = ukupna_cena, novac = novac)

@app.route('/pretraga', methods = ["POST", "GET"])
def pretraga():


		search = request.form['search']

		mc = mydb.cursor()
		mc.execute(f"SELECT * FROM proizvodi WHERE naziv LIKE '%{search}%'")
		rez = mc.fetchall()

		return render_template("showall.html",rez = rez)


@app.route('/novcanik', methods = ["POST"])
def novcanik():
	if "username" in session:
		username = session["username"]

		mc = mydb.cursor()
		mc.execute("SELECT * FROM proizvodi")
		proizvodi = mc.fetchall()
		#return str(proizvodi)
		mc.execute("SELECT * FROM korpa")
		korpa = mc.fetchall()

		mc.execute(f"SELECT * FROM korisnici where username='{username}'")
		trenutni_korisnik_zaista = mc.fetchall()[0]
		#return str(trenutni_korisnik)
		p_useri = []
		trenutni_korisnik = []


		for k in korpa:
			if k[1] == username:
				trenutni_korisnik.append(k)


		for p in proizvodi:
			for t in trenutni_korisnik:
				if t[2] == p[0]:
					p_useri.append(p)


		ukupno = 0
		for p in p_useri:
			ukupno += int(p[5])
		#return str(ukupno)

		mc = mydb.cursor()
		mc.execute(f"SELECT * FROM korisnici WHERE username='{username}'")
		novcanik = mc.fetchall()
		novcanik_sredstva = novcanik[0][5]
		# 
		rezultat = ukupno - novcanik_sredstva
		if (rezultat > 0):
			flash('Nemate dovoljno sredstava!')
			return redirect(url_for('profil',username=username))
		else:
			flash('Uspešna kupovina!')
			mc = mydb.cursor()
			mc.execute(f"DELETE FROM korpa WHERE korisnik_username='{username}'")
			rezultat = abs(rezultat)
			mc = mydb.cursor()
			mc.execute(f"UPDATE korisnici SET novcanik='{rezultat}' WHERE username='{username}'")
			mydb.commit()
			return redirect(url_for('profil',username=username))
		

@app.route('/dodavanje', methods=["POST"])

def dodavanje():
		username = session["username"]
		if request.method == "POST":
			mc = mydb.cursor()
			mc.execute(f"SELECT * FROM korisnici WHERE username = '{username}'")
			tr = mc.fetchall()
			trenutno = tr[0][5]
			novcanik = (request.form["novcanik"])
			append = int(trenutno) + int(novcanik)
			mc = mydb.cursor()
			mc.execute(f"UPDATE korisnici SET novcanik='{append}' WHERE username='{username}'")
			mydb.commit()
			return redirect(url_for('profil',username=username))
		else:
			return redirect(url_for('profil',username=username))

@app.route('/dodaj_u_korpu/<proizvod_id>',methods = ["POST"])
def dodaj_u_korpu(proizvod_id):
	username = session['username']
	mc = mydb.cursor()
	mc.execute(f"INSERT INTO korpa VALUES(null, '{username}', '{proizvod_id}') ")
	mydb.commit()
	return redirect(url_for('show_all'))
@app.route('/delete/<proizvod_id>',methods = ["POST"])
def delete(proizvod_id):
	mc = mydb.cursor()
	mc.execute(f"SELECT * FROM proizvodi WHERE id={proizvod_id}")
	rez = mc.fetchall()

	if 'username' not in session:
		return render_template("showall.html")
	if session['username'] == rez[0][1]:
		mc = mydb.cursor()
		mc.execute(f"DELETE FROM proizvodi WHERE id={proizvod_id}")
		mydb.commit()
	return redirect(url_for('show_all'))
if __name__ == '__main__':
	app.run(debug=True)