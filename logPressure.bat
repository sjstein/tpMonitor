@echo off
color 9
title Pressure monitor
SET /P runtime="Depth monitor - enter time to acquire (min): "
title Pressure monitor started at %time% running for %runtime% min
python tpMonitor.py 192.168.1.121 -t %runtime% -l pressurelog
echo.
echo ************************************************************
echo * Acquisition cycle complete - press a key to close window *
echo ************************************************************
title Pressure monitor acquisition complete
pause >nul