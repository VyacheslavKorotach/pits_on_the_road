/*
 * Created by Keen
 * Modified by Keen 
 * Date: 11/04/2017
 */
#include<stdio.h>
#include<string.h>
#define DEBUG true
String target_phone = "+380675627127"; // Your phone number, not number of 32U4 with A7/GSM/GPS.

void setup()
{
  Serial.begin(115200);
  Serial1.begin(115200);
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(8,OUTPUT);
  digitalWrite(5, HIGH); 
  digitalWrite(4, LOW); 
  digitalWrite(8, LOW); 
  Serial.println("After 2s, test begin!!");
  delay(2000);
  funtion_test();
}

void loop()
{
  if (Serial1.available()>0) {
    Serial.write(Serial1.read());
  }
  if (Serial.available()>0) {
    Serial1.write(Serial.read());
  }
}

void funtion_test(){
   Serial.println("Test begin!!");
   digitalWrite(8, HIGH); 
   delay(3000);       
   digitalWrite(8, LOW); //Power ON..
   Serial.println("A7 Power ON!");
   Serial.println("You may receive the AT   OK"); 
   sendData( "AT",1000,DEBUG);
   delay(500);
   digitalWrite(5, LOW);  //Sleep
   Serial.println("A7 go to sleep now!");
   delay(3000);
   Serial.println("test GPS function");
   testGPS();          //no call, A7 sleeping   
   sendData( "AT",1000,DEBUG);
   delay(500);
   Serial.println("if you receive GPS data,the sleep test failed!");
   digitalWrite(5, HIGH);   // wake up
   delay(1000);
   Serial.println("A7 WAKE UP!"); 
   Serial.println("test whether wake up or not, if OK, A7 wake up"); 
   sendData( "AT",1000,DEBUG);
   delay(500);     
   digitalWrite(4, HIGH); // power off A6
   Serial.println("A7 power off!");
   delay(3000);
   digitalWrite(4, LOW);
   Serial.println("print AT and you not receive OK"); 
   sendData( "AT",1000,DEBUG);
   delay(500); 
   Serial.println("A7 not Respond"); 
   digitalWrite(8, HIGH);           //POWER UP
   delay(3000);       
   digitalWrite(8, LOW);
   delay(3000);
   Serial.println("A7 Power ON!"); 
   Serial.println("................................."); 
   sendData( "AT",1000,DEBUG); //
   delay(1000);
   Serial.println("The funtion is Get GPS..."); 
   testGPS();
   Serial.println("The funtion is Dial Voice Call..."); 
   delay(1000);
   DialVoiceCall();
   Serial.println("The funtion is Send SMS ..."); 
   delay(1000);
   SendTextMessage();
   Serial.println("This function is submit a HTTP request...");
   delay(1000);
   TCP_GPRS();
   Serial.println("All the test of 32U4 with A7 is complete!");
}

void testGPS(void){
  sendData("AT+GPS=1",1000,DEBUG);     
  sendData("AT+GPSRD=1",3000,DEBUG);
  sendData("AT+GPS=0",10000,DEBUG);
}

void TCP_GPRS(){
   sendData("AT+CREG?",5000,DEBUG); //Query network registration
   delay(100);
   sendData("AT+CGATT=1",5000,DEBUG);
   delay(100); 
   sendData("AT+CGDCONT=1,\"IP\",\"WWW.KYIVSTAR.NET\"",2000,DEBUG);//setting PDP parameter 
   delay(100); 
   sendData("AT+CGACT=1,1",10000,DEBUG); //Activate PDP, open Internet service
   delay(100);  
   sendData("AT+CIPSTART=\"TCP\",\"www.baidu.com\",80",10000,DEBUG);
   delay(100);
   sendData("AT+CIPSEND=5,\"12345\"",2000,DEBUG); //Send string "12345" 
   delay(100); 
   sendData("AT+CIPCLOSE",2000,DEBUG);     //Close TCP
   delay(100); 
   /*
     sendData("AT+CREG?",3000,DEBUG);     
     sendData("AT+CGATT=1",1000,DEBUG);
     sendData("AT+CGDCONT=1,\"IP\",\"CMNET\"",1000,DEBUG);
     sendData("AT+CGACT=1,1",1000,DEBUG);
     sendData("AT+CIPSTART=\"TCP\",\"google.com\",80",3000,DEBUG);
     sendData("AT+CIPSEND=80",1000,DEBUG);
     sendData("GET http://www.google.com HTTP/1.0\r\n",100,DEBUG);
     */
}

void SendTextMessage()
{ 
  sendData("",2000,DEBUG);
  sendData("AT+CMGF=1",2000,DEBUG);//Because we want to send the SMS in text mode
  delay(100);
  sendData("AT+CMGS="+target_phone,2000,DEBUG);//send sms message, be careful need to add a country code before the cellphone number
  delay(100);
  sendData("GSM test message!",2000,DEBUG);//the content of the message
  delay(100);
  Serial1.println((char)26);//the ASCII code of the ctrl+z is 26
  delay(100);
}

void DialVoiceCall()
{
   sendData("AT+SNFS=0",5000,DEBUG);
   delay(100);
   sendData("ATD"+target_phone,5000,DEBUG);// "ATD+86137xxxxxxxx"dial the number
   delay(100);
}


String sendData(String command, const int timeout, boolean debug)
{
    String response = "";    
    Serial1.println(command); 
    long int time = millis();
    while( (time+timeout) > millis())
    {
      while(Serial1.available())
      {       
        char c = Serial1.read(); 
        response+=c;
      }  
    }    
    if(debug)
    {
      Serial.print(response);
    }    
    return response;
}

void httpRec(const int timeout){
    String response = "";    
    long int time = millis();
    while( (time+timeout) > millis())
    {
      while(Serial1.available())
      {       
        char c = Serial1.read(); 
        response+=c;
      }  
    }    
    Serial.print(response); 
}
