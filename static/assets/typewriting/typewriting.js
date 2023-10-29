function typeWriter(elementid,sampletext,speed) {
    var i=0;
    function task(){
        if(i < sampletext.length){
            document.getElementById(elementid).innerHTML += sampletext.charAt(i);
            i++
            setTimeout(task, speed);
        }
            
        
    }   
    
    task();
  }
