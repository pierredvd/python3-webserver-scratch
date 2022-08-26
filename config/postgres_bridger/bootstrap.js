
function Bridge(listenPort, bridgePort){

    const Net = require('net');
    const LISTEN_PORT = listenPort;
    const BRIDGE_PORT = bridgePort;
    var __server = null;


    function __construct(){
        __restartServer();
    }

    function __bridge(socketFrom, socketTo){
        socketFrom.on('data', function(data){ if(socketTo!=null  ){ socketTo.write(data); } });
        socketTo.on(  'data', function(data){ if(socketFrom!=null){ socketFrom.write(data); } });
        function unbridge(){
            if(socketTo!=null){
                socketTo.end();
                socketTo.destroy();
            }
            if(socketFrom!=null){
                socketFrom.end();
                socketFrom.destroy();
            }
        }
        socketFrom.on('error'  , function(){ unbridge(); });
        socketFrom.on('timeout', function(){ unbridge(); });
        socketFrom.on('close'  , function(){ unbridge(); });
        socketTo.on(  'error'  , function(){ unbridge(); });
        socketTo.on(  'timeout', function(){ unbridge(); });
        socketTo.on(  'close'  , function(){ unbridge(); });
    }

    function __restartServer(callback){
        if(__server==null){
            __server = Net.createServer(function(socket){
                try{
                    var socketbridge = new Net.Socket();
                    socketbridge.connect(BRIDGE_PORT, '127.0.0.1', function(err){
                        if(!err){
                            __bridge(socket, socketbridge);
                        } else {
                            socket.end();
                            socket.destroy();
                        }
                    });
                } catch(e){
                    socket.end();
                    socket.destroy();
                }
            }).on('error', function(e){
                __server.close();
            }).on('close', function(e){
                process.nextTick(function(){
                    __server = null;
                    __restartServer(callback);
                });
            }).listen(LISTEN_PORT, function(){
                console.log('Postgesql bridger is now listening port ', LISTEN_PORT);
            });
        }
    }

    __construct();

}

if(process.argv.length==2){
    const Spawn  = require('child_process').spawn;
    const Worker = Spawn(process.argv[0], [process.argv[1], 5432, 5433], {
        detached: true,
        stdio: 'ignore'
    });

} else {

    const Run = new Bridge(process.argv[2], process.argv[3]);

}
