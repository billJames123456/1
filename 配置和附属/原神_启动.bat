@echo off  
echo ����mysql...
echo --------------------------------------------------------------------------------------------
net start mysql

echo ����ǰ��
echo --------------------------------------------------------------------------------------------
G:
cd G:\Picture-Master\SpringBoot-master\MemoryFront
npm run serve
