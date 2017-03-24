for name in $(kcpcmd -s ${DEST}:7147 client-list | grep proxy | cut -f2 -d  ' ' ) ; do kcpcmd -rs ${DEST}:72${name:2:2} capture-list  | grep --label=$name -H  capture-list ; done
