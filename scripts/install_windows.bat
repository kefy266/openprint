@echo off
REM ===================================================================
REM  OpenPrint - scripts\ klasîrÅ iáindeki kurulum giriü noktasç
REM
REM  Geráek iü mantçßç kîk dizindeki install.bat dosyasçndadçr; burada
REM  yalnçzca yînlendirilir, bîylece iki kopyasç bakçm gerektirmez.
REM
REM  Dosya kurallarç (bilerek):
REM    kodlama   : Windows-857 (TÅrkáe OEM, tek bayt/karakter)
REM    satçr sonu: CRLF
REM    BOM yok, chcp yok, emoji yok
REM
REM  Bu kurallar bozulursa cmd.exe satçrlarçn baüçndaki karakterleri
REM  yutar ve üîyle bir áîp akçüç gîrÅnÅr:
REM    'ndows' is not recognized as an internal or external command
REM  Bu bir kod hatasç deßil, kodlama hatasçdçr.
REM ===================================================================
cd /d "%~dp0.."
call "%~dp0..\install.bat"
exit /b %errorlevel%
