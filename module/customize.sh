SKIPMOUNT=false
PROPFILE=true
POSTFSDATA=false
LATESTARTSERVICE=false
Market_Name=`getprop ro.product.marketname`
Device=`getprop ro.product.device`
Model=`getprop ro.product.model`
Version=`getprop ro.build.version.incremental`
Android=`getprop ro.build.version.release`
CPU_ABI=`getprop ro.product.cpu.abi`
CommonPath=$MODPATH/common
print_modname() {
  ui_print "*******************************"
  ui_print " Sửa đổi máy: $MODNAME "
  ui_print " Tác giả Module: @Usagi79 "
  ui_print " Thông tin liên quan：t.me/Usagi79"
  ui_print " Máy: $Market_Name"
  ui_print " Mã thiết bị: $Device"
  ui_print " Mã định danh: $Model"
  ui_print " Phiên bản Android: Android $Android"
  ui_print " Phiên bản hệ thống: $Version"
  ui_print " CPU kiến trúc: $CPU_ABI"
  ui_print "*******************************"
}

print_modname

on_install() {
  ui_print "- Giải nén các tệp"
  unzip -o "$ZIPFILE" 'system/*' -d $MODPATH >&2
}

set_permissions() {
  set_perm_recursive  $MODPATH  0  0  0755  0644
 
}

mv  ${CommonPath}/*  $MODPATH
rm  -rf ${CommonPath}

