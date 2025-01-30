!macro customHeader
    RequestExecutionLevel admin
!macroend

!macro customInit
    SetRegView 64
!macroend

!macro customInstall
    ; 添加防火墙规则
    nsExec::ExecToLog 'netsh advfirewall firewall add rule name="网格交易系统" dir=in action=allow program="$INSTDIR\网格交易系统.exe" enable=yes'
    nsExec::ExecToLog 'netsh advfirewall firewall add rule name="网格交易系统" dir=out action=allow program="$INSTDIR\网格交易系统.exe" enable=yes'
    
    ; 设置环境变量
    EnVar::SetHKCU
    EnVar::AddValue "PATH" "$INSTDIR"
!macroend

!macro customUnInstall
    ; 删除防火墙规则
    nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="网格交易系统"'
    
    ; 删除环境变量
    EnVar::SetHKCU
    EnVar::DeleteValue "PATH" "$INSTDIR"
!macroend 