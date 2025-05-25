[启动步骤]
1.启动mysql服务
2.启动redis服务
3.启动后端进程
4.启动前端进程

[改动]
1.login.vue 第99行下划线_this.$message
2.main.js 
// 服务端请求路径
Vue.prototype.$serveUrL = 'http://localhost:8999'
3.application里
#数据库配置信息
server.port=8088 改成了8999
4.需启动redis和mysql 再启动后端 再启动前端
5.redis密码配空

[所需依赖]
1.阿里云图像识别
2.springboot 2.7 //success
3.redis 3.2 //success
4.mysql 8.0 //success
5.mybatis 3.5.2 //success
6.jjwt //success
7.thumbnailator //success
8.vue 2.6.7  elementui 2.15.8 //success
9.echarts.js //suceess
10.axios  //success
11.Node.js:14.18+ //success
12.Npm:6.14.5+ //success

