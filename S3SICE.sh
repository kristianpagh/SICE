#!/bin/bash

CLD=/scratch/ms/dk/nhx/SICE
y=2021
LD=$CLD
DATA=cca:$CLD/$y
for m in 03 04 05 06 07 08 09 10
do
  for d in `seq -w 1 31`
  do
    [ "$d" = "31" -a "$m" = "04" ] && continue 
    [ "$d" = "31" -a "$m" = "06" ] && continue 
    [ "$d" = "31" -a "$m" = "09" ] && continue 
    ISO8601=$y-$m-$d
    if [ ! -s $LD/BBA_combination_$ISO8601.tif ]
    then
      yesterday=`date -d "$ISO8601 -1-day" +%Y-%m-%d`
      twodays=`date -d "$ISO8601 -2-day" +%Y-%m-%d`
      echo "open tankur.vedur.is" > $CLD/tmp/lftpinput
      echo "user jbox FTP4jbox" >> $CLD/tmp/lftpinput
      echo "cd inc/SICE/NRT" >> $CLD/tmp/lftpinput
      #for area in FransJosefLand Greenland Iceland NorthernArcticCanada Norway NovayaZemlya SevernayaZemlya SouthernArcticCanada Svalbard 
      for area in FransJosefLand Greenland Iceland NorthernArcticCanada NovayaZemlya SevernayaZemlya SouthernArcticCanada Svalbard 
      do
        [ -s $CLD/$area/BBA_combination_$ISO8601.tif ] || echo "get $area/$ISO8601/BBA_combination.tif -o $CLD/$area/BBA_combination_$ISO8601.tif" >> $CLD/tmp/lftpinput
      done
      echo "bye" >> $CLD/tmp/lftpinput
      /usr/bin/lftp < $CLD/tmp/lftpinput > $CLD/tmp/lftpoutput 2>&1
      if [ -s $LD/BBA_combination_$yesterday.tif ] 
      then
        gdalwarp -te -1600000 -3400000 2744000 1154000 $LD/BBA_combination_$yesterday.tif `ls $CLD/{F,G,I,N,S}*/BBA_combination_$ISO8601.tif` $LD/BBA_combination_$ISO8601.tif
      elif [ -s $LD/BBA_combination_$twodays.tif ] 
      then
        gdalwarp -te -1600000 -3400000 2744000 1154000 $LD/BBA_combination_$twodays.tif `ls $CLD/{F,G,I,N,S}*/BBA_combination_$ISO8601.tif` $LD/BBA_combination_$ISO8601.tif
      else
        gdalwarp -te -1600000 -3400000 2744000 1154000 `ls $CLD/{F,G,I,N,S}*/BBA_combination_$ISO8601.tif` $LD/BBA_combination_$ISO8601.tif
      fi
    fi
    gdalwarp -t_srs '+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 +x_0=0 +y_0=0 +ellps=sphere +R=6371000 +units=m +no_defs' $LD/BBA_combination_$ISO8601.tif $LD/sphere_BBA_combination_$ISO8601.tif
    #/usr/local/apps/gdal/2.1.1/LP64/bin/gdal_calc.py -A $LD/sphere_BBA_combination_$ISO8601.tif --outfile=$LD/tmp.tif --calc="nan_to_num(A)"; mv $LD/tmp.tif $LD/sphere_BBA_combination_$ISO8601.tif
    gdal_translate -of netCDF -ot Float32 $LD/sphere_BBA_combination_$ISO8601.tif $LD/sphere_BBA_combination_$ISO8601.nc && rm -f $LD/sphere_BBA_combination_$ISO8601.tif
    scp $LD/sphere_BBA_combination_$ISO8601.nc $DATA/ && rm -f $LD/sphere_BBA_combination_$ISO8601.nc
  done
done
