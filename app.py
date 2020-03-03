import os
import sys
import click

from _datetime import datetime

from flask import Flask,render_template,request,url_for,redirect,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash 
from flask_login import LoginManager,UserMixin,login_user,logout_user,login_required,current_user

app = Flask(__name__)

WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///' # 如果是Windows系统
else:
    prefix = 'sqlite:////' # Mac,Linux

#flask配置：Flask.config字典（写入配置的语句一般会放到扩展类实例化之前）
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path,'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # 关闭对模型修改的监控
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY','dev')

db = SQLAlchemy(app)

#创建数据库模型类
class User(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key=True) # 唯一(主键)
    name = db.Column(db.String(4))
    username = db.Column(db.String(20))  #用户名
    password_hash = db.Column(db.String(128)) #密码散列值

    def set_password(self,password):
        self.password_hash = generate_password_hash(password)
    def validate_password(self,password):
        return check_password_hash(self.password_hash,password)

class Ariticles(db.Model):
    id = db.Column(db.Integer,primary_key=True) # 唯一(主键)
    title = db.Column(db.String(60),unique=True)
    content = db.Column(db.Text)  # 内容
    author = db.Column(db.String(16)) #作者
    pubdate = db.Column(db.DateTime,index=True,default=datetime.utcnow) # 添加时间

#自定义指令
@app.cli.command()
@click.option('--drop',is_flag=True,help='删除之后再创建')
def initdb(drop):
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('初始化数据库')

# 自定义命令forge，把数据写入到数据库
@app.cli.command()
def forge():
    db.create_all()
    name = "李黑皮"
    ariticles = [
        {'title':'python基础','content':'hello1','author':'作者one'},
        {'title':'python入门','content':'hello2','author':'作者two'},
        {'title':'python初级','content':'hello3','author':'作者there'},
        {'title':'python高级','content':'hello4','author':'作者four'},
    ]
    user = User(name=name)
    db.session.add(user)
    for a in ariticles:
        ariticle = Ariticles(title=a['title'],content=a['content'],author=a['author'])
        db.session.add(ariticle)
    db.session.commit()
    click.echo('数据导入完成')

# 生成admin账号的函数
@app.cli.command()
@click.option('--username',prompt=True,help="用来登录的用户名")
@click.option('--password',prompt=True,hide_input=True,confirmation_prompt=True,help="用来登录的密码")
def admin(username,password):
    db.create_all()
    user = User.query.first()
    if user is not None:
        click.echo('更新用户')
        user.username = username
        user.set_password(password)
    else:
        click.echo('创建用户')
        user = User(username=username,name="Admin")
        user.set_password(password)
        db.session.add(user)
    
    db.session.commit()
    click.echo('创建管理员账号完成')

# Flask-login 初始化操作
login_manager = LoginManager(app)   # 实例化扩展类

@login_manager.user_loader
def load_user(user_id):   # 创建用户加载回调函数，接受用户ID作为参数
    from app import User
    user = User.query.get(int(user_id))
    return user

login_manager.login_view = 'login'
login_manager.login_message = "没有登录"


#首页
@app.route('/',methods=['GET','POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('输入错误')
            return redirect(url_for('index'))
        user = User.query.first()
        if username == user.username and user.validate_password(password):
            login_user(user)  # 登录用户
            flash('登录成功')
            return redirect(url_for('index'))  # 登录成功返回首页
        flash('用户名或密码输入错误')
        return redirect(url_for('index'))
    # if request.method == "POST":
    #     if not current_user.is_authenticated:
    #         return redirect(url_for('index'))
    #     #获取表单数据
    #     title = request.form.get('title')
    #     year = request.form.get('year')

    #     #验证title不为空且不大于60，year不大于4
    #     if not title or not year or len(title)>60 or len(year)>4:
    #         flash("输入错误")
    #         return redirect(url_for('index')) #重定向会首页

    #     movie = Movie(title=title,year=year)  #创建记录
    #     db.session.add(movie) #添加到数据库会话
    #     db.session.commit()  #提交数据库会话
    #     flash('数据创建成功')
    #     return redirect(url_for('index'))
    ariticles = Ariticles.query.all()   
    return render_template('index.html',ariticles=ariticles) #render_template渲染html
    # return "heheh"

#编辑电影信息页面
@app.route('/ariticle/edit/<int:ariticle_id>',methods=['POST','GET'])
@login_required
def edit(ariticle_id):
    ariticle = Ariticles.query.get_or_404(ariticle_id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title or not content or len(title)>60 or len(content)>4:
            flash('输入错误')
            return redirect(url_for('edit',ariticle_id=ariticle_id))
        
        ariticle.title = title
        ariticle.content = content
        db.session.commit()
        flash('电影信息已经更新')
        return redirect(url_for('index'))
    return render_template('edit.html',ariticle=ariticle)

#删除信息
@app.route('/ariticle/delete/<int:ariticle_id>',methods=['POST'])
@login_required  # 认证保护
def delete(ariticle_id):
    ariticles = Ariticles.query.get_or_404(ariticle_id)
    db.session.delete(ariticles)
    db.session.commit()
    flash("删除成功！")
    return redirect(url_for('index'))


# @app.errorhandler(404) #传入要处理的错误代码
# def page_not_found(e):
#     return render_template('404.html'),404

@app.context_processor # 模板上下文处理函数
def inject_user():
    user = User.query.first()
    return dict(user=user)

# # 设置页面
# @app.route('/settings',methods=['POST','GET'])
# @login_required
# def settings():
#     if request.method =='POST':
#         name = request.form['name']

#         if not name or len(name)>20:
#             flash('输入错误')
#             return redirect(url_for('settings'))

#         current_user.name = name
#         db.session.commit()
#         flash('设置name成功')
#         return redirect(url_for('index'))

#     return render_template("settings.html")


# 用户登录 flask提供的login_user()函数

    

# 用户登出
@app.route('/logout')
def logout():
    logout_user()
    flash('退出登录')
    return redirect(url_for('index'))

