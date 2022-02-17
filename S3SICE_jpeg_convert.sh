#!/bin/bash

y=2021
CLD=/scratch/ms/dk/nhx/SICE/$y
#for m in `seq -w 03 10`
for m in 08 09 10
do
  [ $m -lt 3 -o $m -gt 10 ] && continue
  for d in `seq -w 1 31`
  do
    [ $m -eq 4 -a $d -eq 31 ] && continue
    [ $m -eq 6 -a $d -eq 31 ] && continue
    [ $m -eq 9 -a $d -eq 31 ] && continue
    ISO8601=$y-$m-$d
    [ -s $CLD/BBA_combination_$ISO8601.tif ] || ( echo $CLD/BBA_combination_$ISO8601.tif does not exist!; exit 1)
    gdal_translate -of jpeg -scale 0 1 0 255 $CLD/BBA_combination_$ISO8601.tif $CLD/BBA_combination_$ISO8601.jpg
    convert -scale 20% -pointsize 40 -fill red -annotate +30+50 "$ISO8601" $CLD/BBA_combination_$ISO8601.jpg $CLD/BBA_combination_$ISO8601.jpg
    #[ -s $CLD/sphere_BBA_combination_$ISO8601.nc ] || ( echo $CLD/sphere_BBA_combination_$ISO8601.nc does not exist!; exit 1)
    #gdal_translate -of jpeg -scale 0 1 0 255 $CLD/sphere_BBA_combination_$ISO8601.nc $CLD/sphere_BBA_combination_$ISO8601.jpg
    #convert -scale 20% -pointsize 40 -fill red -annotate +30+50 "$ISO8601" $CLD/sphere_BBA_combination_$ISO8601.jpg $CLD/sphere_BBA_combination_$ISO8601.jpg
  done
done
exit 0
