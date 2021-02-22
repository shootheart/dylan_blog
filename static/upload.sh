#! /bin/bash

set -x
conf="/c/Users/liuchong/AppData/Roaming/picgo/data.json"
path="$(echo $* | awk '{print $1}')/"
pics="$(echo $* | awk '{$1=""; print $0}')"

sed -i /path/{"s|\:.*|\: \"$path\"|"} $conf
echo -n "$(/e/PicGo/PicGo.exe upload $pics | grep https)" &
sleep $((5*($#-1)))
ps -ef | grep "PicGo" | awk '{print $2}' | xargs kill >> /dev/null