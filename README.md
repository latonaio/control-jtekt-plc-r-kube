# control-jtekt-plc-r-kube  
ジェイテクト製のPLCのレジスタに登録されたメッセージを読み込むマイクロサービスです。  
メッセージの送受信方法およびフォーマットはバイナリ形式です。  

## 1.動作環境  

* OS: Linux  
* CPU:ARM/AMD/Intel  

## 2.対応している接続方式  
* Ethernet接続  

## 3.IO  

### Input  
PLCのレジスタへの読み取りを定期実行し、バイナリで構成された電文を取得します。  

### Output  
電文の内容を元にkanbanへデータの投入を行います。  

## 4.関連するマイクロサービス  
control-jtekt-plc-w-kube  