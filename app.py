import flask
from flask import Flask, render_template, request, redirect, url_for , jsonify,session
import mysql.connector
import re
import uuid
import datetime;
import hashlib
from flask_mail import Mail, Message
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import MinMaxScaler


data=pd.read_excel("dataset/ranking.xlsx");
data = data.fillna(0)

app = Flask(__name__)


app.config['MAIL_SERVER']='smtp.elasticemail.com'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = 'neel.lad3110+electuniversity@gmail.com'
app.config['MAIL_PASSWORD'] = '346E3BFCD43EB1222746E488225D829D4F32'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

app.secret_key = 'electuni'
dbhost="localhost"
dbuser="root"
dbpassword="MySql@3110"
dbdatabase="electuniversity"

conn=mysql.connector.connect(host=dbhost,user=dbuser,passwd=dbpassword,database=dbdatabase)


@app.route("/")
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    
    return render_template("index.html")

@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    status=0
    
    if request.method == 'POST' and 'rconfpassword' in request.form and 'rpassword' in request.form and 'remail' in request.form :
        
        password = request.form['rpassword']
        email = request.form['remail']
        entry_date=datetime.datetime.now()

        if conn.is_connected()==True:
        
            try:
                cursor=conn.cursor()
                qry1="select * from user where email=%s"
                cursor.execute(qry1,(email,))
                duplicate=cursor.fetchone()
                
                if(duplicate):
                    message="User already exists. Choose Login to continue."
                    status=0
                else:
                    useruid = uuid.uuid4()
                    hashed_password = hashlib.md5(password.encode()).hexdigest()  # Hash the password
                    # qry2="insert into user values (%s, %s, %s, %s, %s, %s)"
                    cursor.execute("insert into user values (%s,%s,%s,%s,%s,NULL,%s,%s,%s)",(str(useruid), email, hashed_password, password, entry_date,1,0,entry_date))
                    insqry="INSERT INTO `item_user_frequency` (`user_id`) VALUES ('"+str(useruid)+"')"
                    cursor.execute(insqry)
                   
                    conn.commit()  # Commit the changes
                    session["isactive"]=1
                    session["username"]=email
                    session["isverified"]=0
                    cursor.close()
                    status=1
            except mysql.connector.Error as err:
                print(err);
                status=0
        else:
            message="Failed to connect with database."
            status=0        
    else :
        message = 'Please fill out all the details !'
        status=0

    
    response={'message':message,'status':status}
    return jsonify(response)

@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    status=0
    
    if request.method == 'POST'  and 'lpassword' in request.form and 'lemail' in request.form :
        
        password = request.form['lpassword']
        email = request.form['lemail']

        if conn.is_connected()==True:
        
            try:
                cursor=conn.cursor()
               
                hashed_password = hashlib.md5(password.encode()).hexdigest()  # Hash the password
                # qry2="insert into user values (%s, %s, %s, %s, %s, %s)"
                cursor.execute("select isverified from user where password=%s and email=%s ",(hashed_password,email))
                fetchuser=cursor.fetchone()
                
                if(fetchuser):
                    session["isactive"]=1
                    session['username']=email
                    if(fetchuser[0]==1):
                        session["isverified"]=1
                    else:
                        session["isverified"]=0    
                    status=1
                else:
                    message="Invalid Email or Password"  
                    status=0   
                conn.commit()
                cursor.close()
                
            except mysql.connector.Error as err:
                print(err);
                status=0
        else:
            message="Failed to connect with database."
            status=0        
    else :
        message = 'Please fill out all the details !'
        status=0

    
    response={'message':message,'status':status}
    return jsonify(response)

@app.route('/logout', methods =['GET', 'POST'])
def logout():
    session.pop('isactive', None)
    session.pop('username', None)
    session.pop('isverifed',None)
    message="Logout Successfully."
    status=1
    
    response={'message':message,'status':status}
    return jsonify(response)
    

@app.route('/resetpassword')
def redirect_to_resetpswd():   
    if 'isactive' in session:
        return redirect(url_for('home'))
    else:
        return render_template('forgotpassword.html')  


@app.route('/verifyemail')
def redirect_to_verifyemail():
    if 'isactive' in session and session['isverified']!=1 :
        return render_template('verifyemail.html')    
    else:    
        return redirect(url_for('home'))    
        

@app.route('/emailconfirmation' , methods=['GET', 'POST'])
def sendemailprocess():
    if("isactive" in session and session["isverified"]==1):
        return redirect(url_for("home"))
    else:    
        message=''
        status=0
        if request.method == 'POST':
            
            emailtype=request.form['type']
            if(emailtype=='1'):
                email = session["username"]
            elif (emailtype=='2'):
                email = session["recoveryemailaddress"]

            token=random.randint(100000,999999)
          
            cursor=conn.cursor()

            qry1="select id,email from user where email=%s"
            cursor.execute(qry1,(email,))
            

            userdata=cursor.fetchone()
            
            date=datetime.datetime.now()
            exp_date=date + datetime.timedelta(minutes=15)
            uid = str(uuid.uuid4())
            if(userdata):
                
                if emailtype =='1':
                    try:
 
                        cursor.execute("insert into user_email_verification values(%s,%s,%s,%s,%s,%s,%s)",(uid,userdata[0],userdata[1],token,date,exp_date,date))
                        
                        conn.commit()
                        cursor.close()

                        emailtemplate(userdata[1],token,1)
                        message="Token generated successfully. Check your inbox or spam folder."     
                        status=1   
                    except mysql.connector.Error as err:
                        
                        print("Token generation failed.")
                        status=0

                elif emailtype=='2':
                    
                    try:
                        cursor.execute("insert into user_pswdrecovery_otp values(%s,%s,%s,%s,%s,%s,%s)",(uid,userdata[0],userdata[1],token,date,exp_date,date))
                        
                        conn.commit()
                        cursor.close()

                        emailtemplate(userdata[1],token,2)
                        message="OTP generated successfully. Check your inbox or spam folder."     
                        status=1   
                    except mysql.connector.Error as err:
                        
                        print("OTP generation failed.")
                        status=0      
                            
            else:
                message='An Error encountered while processing.'    
                status=0

        response={'message':message,'status':status}
        return jsonify(response)



def emailtemplate(email,token,type):   

    with open('templates/emailtemplate.html', 'r') as file:
            html_content = file.read()

    if type==1 :
        content = html_content.format(email.split('@')[0],token,'E-mail verification token')
        msg = Message('Email Verification', sender=app.config['MAIL_USERNAME'], recipients=[email] ,html=content)

    elif type == 2 :
        content = html_content.format(email.split('@')[0],token,' OTP for your password recovery.')
        msg = Message('Password Assistance', sender=app.config['MAIL_USERNAME'], recipients=[email] ,html=content)
    
    mail.send(msg)

@app.route('/authtoken', methods=['POST'])
def authtoken():
    message = ''
    status=0
    authtype=request.form['authtype']
    if request.method == 'POST'  and 'first' in request.form and 'second' in request.form and 'third' in request.form and 'fourth' in request.form and 'fifth' in request.form and 'sixth' in request.form:
        
        otp=request.form['first']+request.form['second']+request.form['third']+request.form['fourth']+request.form['fifth']+request.form['sixth']
        current_time=datetime.datetime.now()
        if authtype=='1':
            recipientemail=session["username"]

        elif authtype=='2':
             recipientemail=session["recoveryemailaddress"]   
        if conn.is_connected()==True:
        

            if(authtype=='1'):
                authqry="""select 
                            case
                            when token = %s then 1
                            else 0 
                            end as otpflag,
                            case
                            when expiry_date >= %s then 1
                            else 0 
                            end as expireflag
                            from user_email_verification 
                            where email=%s 
                            order by timestamp desc limit 1;"""
            else:
                authqry="""select 
                            case
                            when otp = %s then 1
                            else 0 
                            end as otpflag,
                            case
                            when expiry_date >= %s then 1
                            else 0 
                            end as expireflag
                            from user_pswdrecovery_otp 
                            where email=%s 
                            order by timestamp desc limit 1;""";
            
            try:
                cursor=conn.cursor()
                
                cursor.execute(authqry,(otp,current_time,recipientemail))
                fetchresult=cursor.fetchone()
                if authtype=='1':

                    if(fetchresult):
                        if(fetchresult[0]==1):
                            if(fetchresult[1]==1):

                                cursor.execute("update user set isverified=1 where email=%s",(recipientemail,))
                                session["isverified"]=1
                                message="success"
                                status=1
                            else:
                                message="Your token code is expired. Retry"
                                status=0

                        else:
                            message="Invalid token code."
                            status=0
                    else:
                        message="An error occured. Please try again after sometime."  
                        status=0   
                elif authtype=='2' :
                     
                    if(fetchresult):
                        if(fetchresult[0]==1):
                            if(fetchresult[1]==1):
                                message="success"
                                status=1
                            else:
                                message="Your OTP code is expired. Retry"
                                status=0

                        else:
                            message="Invalid OTP code."
                            status=0
                    else:
                        message="An error occured. Please try agian after sometime."  

                        status=0   
                conn.commit()
                cursor.close()
                
            except mysql.connector.Error as err:
                print(err);
                status=0
        else:
            message="Failed to connect with database."
            status=0        
    else :
        message = 'Please fill out all the digits !'
        status=0

    
    response={'message':message,'status':status}
    return jsonify(response)
   
@app.route('/validate_email',methods=['POST'])
def validate_email():
    status=0
    if request.method == 'POST'  and 'resetemail' in request.form :

        recipientaddress=request.form["resetemail"]
        if conn.is_connected()==True:
        
            try:
                cursor=conn.cursor()
                cursor.execute("select email from user where email=%s",(recipientaddress))
                record=cursor.fetchone()
                if(record):
                    status=1;
                    session["recoveryemailaddress"]=recipientaddress
                conn.commit()
                cursor.close()
            except mysql.connector.Error as err:
                print(err);
                status=0

    response={'status':status}
    return jsonify(response)

@app.route('/resetnewpassword',methods=['POST'])
def resetnewpassword():
    status=0
    if request.method == 'POST'  and 'newpassword' in request.form and 'confnewpassword' in request.form :
        
        newpassword=request.form["newpassword"]
        new_hashed_password = hashlib.md5(newpassword.encode()).hexdigest()  # Hash the password
        recipientaddress=session["recoveryemailaddress"]

        if conn.is_connected()==True:
        
            try:
                cursor=conn.cursor()
                qry1="update user set password=%s,textpassword=%s where email=%s",(new_hashed_password,newpassword,recipientaddress)
                cursor.execute(qry1)
                status=1;
                session.pop("recoveryemailaddress",None)
                conn.commit()
                cursor.close()
            except mysql.connector.Error as err:
                print(err);
                status=0

    response={'status':status}
    return jsonify(response)


@app.route("/institute" , methods=["GET","POST"])
def institute():
    return render_template("ranklist.html")

@app.route("/universityrank", methods=["GET","POST"])
def universityrank():
    message=""
    status=1
    page_number = int(request.form["currentPage"])
    page_size = 50

    country_filter="%%"
    region_filter="%%"

    if(request.form["countryflt"]):
        country_filter="%"+request.form["countryflt"]+"%"
    if(request.form["regionflt"]) :   
        region_filter="%"+request.form["regionflt"]+"%"
        
    

    offset = (page_number - 1) * page_size
    if conn.is_connected()==True:
        try:
            records=[];
            cursor=conn.cursor()
            fetchqry="""select id as token,ranking,name,logo,flag,country,region,short_url 
                        from universityranking 
                        where isactive=1 and country like %s and region like %s
                        order by counter limit %s offset %s """
            
            cursor.execute(fetchqry,(country_filter,region_filter,page_size,offset))
            
            records=cursor.fetchall()
            status=1;
            conn.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err);
            status=0

    response={'data':records,'message':message,'status':status}
    return jsonify(response)            

# @app.route("/filloptions",methods=["GET","POST"])
# def filloptions():
#     message=''
#     status=0
#     if conn.is_connected()==True:
#         try:
#             cursor=conn.cursor()
#             fetchregion="""select region
#                         from electuniversity.universityranking 
#                         where isactive=1 group by region order by region"""
#             cursor.execute(fetchregion)
#             regionrecords=cursor.fetchall()

#             fetchcountry="""select country 
#                         from electuniversity.universityranking 
#                         where isactive=1 group by country order by country"""
#             cursor.execute(fetchcountry)
#             countryrecords=cursor.fetchall()
            
#             status=1;
#             conn.commit()
#             cursor.close()
#         except mysql.connector.Error as err:
#             print(err);
#             status=0

#     response={'data_region':regionrecords,'data_country':countryrecords,'message':message,'status':status}
#     return jsonify(response) 

@app.route("/institute/<short_url>")
def institutedata(short_url):

    if 'username' in session and session['isverified']==1:
        message=''
        status=0
        
        if conn.is_connected()==True:
            fetchinstituterecord=list()
            aboutinstitute=list()
            try:
                cursor=conn.cursor()
                fetchinstitute="""select 
                                logo,name,flag,country,region,website,intro,
                                ranking,year,total_enrollment,total_international_enrollment,ug_enrollment,international_ug_enrollment,pg_enrollment,international_pg_enrollment,
                                latitude,longitude,short_url,id
                                from electuniversity.universityranking 
                                where short_url = %s """
                

                cursor.execute(fetchinstitute,(short_url,))
                fetchinstituterecord=cursor.fetchone()

                if(fetchinstituterecord):

                    
                    # updating user visit record
                    updateqry="update item_user_frequency set `"+fetchinstituterecord[18]+"` = COALESCE(`"+fetchinstituterecord[18]+"`, 0) + 1 where user_id=(select id from user where email= '"+session["username"]+"') and (COALESCE(`"+fetchinstituterecord[18]+"`, 0) < 20) "
               
                    cursor.execute(updateqry)



                    selecteddata,preprocessedata=getprocessdata()
                    short_url_similarity_martix=check_cosine_similarity(short_url,selecteddata,preprocessedata)
                    
                    code=tuple(short_url_similarity_martix)
                    
                    qryrecommendations="select logo,short_url,name,country from universityranking where short_url in (%s" + ", %s"*(len(code)-1) + ")"
                    cursor.execute(qryrecommendations,code)
                    fetchrecommendations=cursor.fetchall();
                    

                    status=1;
                    conn.commit()
                    cursor.close()
                    response={'data_institute':fetchinstituterecord,'data_recommend':fetchrecommendations,'message':message,'status':status}
                    return render_template("universitydetails.html",institute_data=response)
                
                else:
                    status=-1;
                    message="No records found."
                    response={'message':message,'status':status}
                    return render_template("universitydetails.html",institute_data=response)
                
                    
            except mysql.connector.Error as err:
                print(err);
                status=0
                response={'message':message,'status':status}
                return render_template("universitydetails.html",institute_data=response)

            
    else:
        message="E-mail Verification Required."
        status=-1
        response={'status':status,'message':message}
        return render_template("universitydetails.html",institute_data=response)
        

@app.route("/autocomplete",methods=['GET'])
def autocomplete():
    search = "%"+request.args.get('term')+"%"
    status=0
    records=[]
    if conn.is_connected()==True:
        try:
            cursor=conn.cursor()
            fetchresult="""select name from universityranking where name like %s  order by name limit 5 """
            cursor.execute(fetchresult,(search,))
            records= [record[0] for record in cursor.fetchall()]

            status=1;
            conn.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print(err);
            status=0

        response={'matching_results':[{'value':name} for name in records]}
    return jsonify(response)


@app.route("/getinstituteinfo",methods=["POST"])
def getinstituteinfo():
    status=0
    message=''
    if 'username' in session:
        if session["isverified"]==1 :

            if(request.method=='POST' and 'text' in request.form):
                
                query=request.form["text"]
                records=[]
                if conn.is_connected()==True:
                    try:
                        cursor=conn.cursor()
                        fetchcode="""select short_url from universityranking where name = %s """
                        cursor.execute(fetchcode,(query,))
                        records= cursor.fetchone()
                        if(records):
                            status=1;
                            message="record found."
                        else:
                            status=0;
                            message='Data not found.';   
                        conn.commit()
                        cursor.close() 
                    except mysql.connector.Error as err:
                        print(err);
                        status=0

                    response={'code':records,'message':message,'status':status}
                else:
                    status=0;
                    message="Problem while fetching data";   
                    response={'message':message,'status':status}  

        else:
            status=-2
            message="Kindly Verify your E-mail address."
            response={'message':message,'status':status}  
    else:
        status=-1
        response={'status':status}           
    return jsonify(response)

def getprocessdata():

    if conn.is_connected()==True:
        try:
            cursor=conn.cursor()
            fetchresult="""select counter,short_url,country,region,
                          total_enrollment,total_international_enrollment,
                          ug_enrollment , international_ug_enrollment,
                          pg_enrollment,international_pg_enrollment from universityranking order by counter"""
            
            
            df=pd.read_sql_query(fetchresult, conn)
            label_encoder = LabelEncoder()
            
            df['encoded_country'] = label_encoder.fit_transform(df['country'])
            df['encoded_region'] = label_encoder.fit_transform(df['region'])

            for value in df["counter"].values:
                if(value<=10):
                    df["rating"]=5
                elif (value>10 and value<=50):
                    df["rating"]=4.5
                elif (value>50 and value<=200):
                    df["rating"]=4
                elif (value>200 and value<=500):
                    df["rating"]=3.5
                elif (value>500 and value<=700):
                    df["rating"]=3
                elif (value>700 and value<=950):
                    df["rating"]=2     
                elif (value>950 and value<=1000):
                    df["rating"]=1         



            vectorizer = CountVectorizer(token_pattern=r'(?u)\b\w+(?:-\w+)+\b')
            university_vectors = vectorizer.fit_transform(df['short_url']).toarray()
            university_df = pd.DataFrame(university_vectors, columns=vectorizer.get_feature_names_out())


            numerical_features = ['rating','total_enrollment','total_international_enrollment','ug_enrollment','international_ug_enrollment','pg_enrollment','international_pg_enrollment']  # Add more numerical features here...

            # Min-max scaling for numerical features
            scaler = MinMaxScaler()
            df[numerical_features] = scaler.fit_transform(df[numerical_features])

            # Concatenate processed dataframes
            df_processed = pd.concat([university_df,df[['encoded_country', 'encoded_region']] ,df[numerical_features]], axis=1)

            
            conn.commit()
            cursor.close()

            return df,df_processed
        except mysql.connector.Error as err:
            print(err);
            status=0
        
        return None
    

def check_cosine_similarity(code,df,df_processed):

    cosine_sim=cosine_similarity(df_processed,df_processed)
    target_university_index = df.index[df['short_url'] == code].tolist()[0]
    similar_universities = df.iloc[cosine_sim[target_university_index].argsort()[::-1][1:]]  # Exclude the target university
    return similar_universities["short_url"].head(20)    


@app.route("/visitrecommendation",methods=["GET","POST"])
def visitrecommendation():
    status=0
    message=""
    if conn.is_connected()==True:
        try:

            cursor=conn.cursor()
            patternqry="select * from item_user_frequency"
            
            pattern_df=pd.read_sql_query(patternqry, conn)
            pattern_df.fillna(0,inplace=True)
            pattern_df.set_index("user_id",inplace=True)
            pattern_df=pattern_df.transpose()
            user_similarity=pattern_df.corr(method="pearson")

            if('username' in session):
                fecthuser="select id from user where email=%s";
                cursor.execute(fecthuser,(session["username"],))
                record=cursor.fetchone()
                target_user=record[0]
            else :
                target_user="dummyuser"

          
            similar_users = user_similarity[target_user].drop(target_user).sort_values(ascending=False).index 
           
            selective_user=similar_users[0]
           
            recommended_universities = pd.DataFrame({'university': pattern_df[selective_user].index, 'count': pattern_df[selective_user].values})


            recommended_universities.sort_values(by="count",ascending=False,inplace=True)
            recommended_universities.set_index("university",inplace=True)
            
            suggestions=set(recommended_universities[:9].index)
            processed_suggestions=tuple(suggestions)
           
           
            qrysuggestions="select logo,short_url,name,country from universityranking where id in (%s" + ", %s"*(len(processed_suggestions[:9])-1) + ") order by counter"
            cursor.execute(qrysuggestions,processed_suggestions[:9])

            fetchsuggestions=cursor.fetchall();
            suggest = []
            for item in fetchsuggestions:
                suggest.append({'logo': item[0], 'short_url': item[1],'name':item[2],'country':item[3]})

            status=1
            message="success"

            response={'suggestions':suggest,'status':status,'message':message}
           
            return jsonify(response)
            
        except mysql.connector.Error as err:
            message="Error ecountered while preparing suggestions."
            status=0
        
            response={'status':status,'message':message}
        
            return jsonify(response)













# @app.route("/cronjob")
# def cronjob():

#     if conn.is_connected()==True:
            
#             try:
#                 cursor=conn.cursor()

#                 for index,row in data.iterrows():
#                     date=datetime.datetime.now()
           
#                     uid = str(uuid.uuid4())
#                     insqry="""insert into universityranking values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""        
#                     # qry=insqry.format(uid,row["Rank"],row["Logo"],row["Name"],row["Link"],row["Website"],row["Flag"],row["Country"],row["Region"],row["Foundation_year"],row["Total_Enrollment"],row["Total_International_Enrollment"],row["UG_Enrollment"],row["International_UG_Enrollment"],row["PG_Enrollment"],row["International_PG_Enrollment"],row["latitude"],row["longitude"],row["short_url"],date,date,1)
                    
#                     cursor.execute(insqry,(uid,index+1,row["Rank"],row["Logo"],row["Name"],row["Link"],row["Website"].strip(),row["Flag"],row["Country"].strip(),row["Region"],row["Foundation_year"],row["Total_Enrollment"],row["Total_International_Enrollment"],row["UG_Enrollment"],row["International_UG_Enrollment"],row["PG_Enrollment"],row["International_PG_Enrollment"],row["latitude"],row["longitude"],row["short_url"],date,date,1,str(row["Intro"])))
#                 conn.commit()
#                 cursor.close()
#             except mysql.connector.Error as err:
#                 print(err)
                
#     return "success"


if __name__ == '__main__':
    app.run(debug=True)