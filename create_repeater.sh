cat << EOF >> spotseek.sh
#!/bin/bash
# if not found - equals to 1, start it
while true
do
    ps -ef | grep spotseek | grep -v grep | grep -v bash | grep -v spotseek.sh
    if [ \$? -eq 1 ]
    then
        cd $PWD/
        nohup /usr/bin/python3 $PWD/spotseek.py > /dev/null 2>&1 &
    else
        echo "spotseek is running"
    fi
    sleep 30
done
EOF

chmod +x spotseek.sh
