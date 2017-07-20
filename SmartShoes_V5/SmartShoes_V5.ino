#include "I2Cdev.h"
#include "MPU6050_6Axis_MotionApps20.h"
#include <SparkFunBLEMate2.h>
// Arduino Wire library is required if I2Cdev I2CDEV_ARDUINO_WIRE implementation
// is used in I2Cdev.h
#if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
    #include "Wire.h"
#endif
volatile bool mpua_int = false;
volatile bool mput_int = false;
bool mpu_ankle = true;
MPU6050 mpuankle(0x69);
MPU6050 mputoe; // Defines both MPUs
BLEMate2 BLE(&Serial);
uint8_t mpuaIntStatus;   // holds actual interrupt status byte from MPU
uint8_t mputIntStatus;
uint16_t packetSize;    // expected DMP packet size (default is 42 bytes)
uint16_t fifoCount;     // count of all bytes currently in FIFO
uint8_t fifoBuffer[64]; // FIFO storage buffer
//uint8_t fifo2Buffer[64];
Quaternion q;           // [w, x, y, z]         quaternion container
VectorInt16 aa;         // [x, y, z]            accel sensor measurements
VectorInt16 aaReal;     // [x, y, z]            gravity-free accel sensor measurements
VectorInt16 aaWorld;    // [x, y, z]            world-frame accel sensor measurements
VectorFloat gravity;    // [x, y, z]            gravity vector
float ypr[3]; 
float ypr2[3];

void dmpDataReady() {
    mpua_int = true;
}
void otherStupid()
{ mput_int = true;}
void setup() {
    // join I2C bus (I2Cdev library doesn't do this automatically)
    #if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
        Wire.begin();
        //maybe need a wire.setclock line here
    #elif I2CDEV_IMPLEMENTATION == I2CDEV_BUILTIN_FASTWIRE
        Fastwire::setup(400, true);
    #endif
    Serial.begin(57600); // This depends on the baud rate of the BLE
    BLE.setBaudRate(9600);
    BLE.writeConfig();
    BLE.reset();
    Serial.begin(9600);
    BLE.sendData("Working");

    // initialize device
    mpuankle.initialize();
    mputoe.initialize();
    // verify connection
    if( mpuankle.testConnection())
         BLE.sendData("ankle okay");
    if( mputoe.testConnection())
       BLE.sendData("toe okay");
    delay(100);
    if(!mputoe.dmpInitialize())
      BLE.sendData("dmptoe okay");
    if (!mpuankle.dmpInitialize())
      BLE.sendData("dmpankle okay");
     delay(100);
//SET ACCEL/GYRO OFFSET MAYBE?
    mpuankle.setDMPEnabled(true);
    mputoe.setDMPEnabled(true);
    attachInterrupt(digitalPinToInterrupt(2), dmpDataReady, RISING);
    attachInterrupt(digitalPinToInterrupt(3), otherStupid, RISING);
    mpua_int = mpuankle.getIntStatus();
    mput_int = mputoe.getIntStatus();
    BLE.sendData("Instantiated");
    packetSize = mpuankle.dmpGetFIFOPacketSize();
}

void loop() {
  String inputBuffer = "";
  while(!(mput_int || mpua_int))
   {
  while(Serial.available()>0)
   inputBuffer.concat((char)Serial.read());
  inputBuffer = ""; 
   }
   if (mput_int)
    {mpu_ankle = false;
    GetDMP(true);}
   if (mpua_int)
    {mpu_ankle = true;
      GetDMP(true);
    }
}
void GetDMP(bool Startup) { // Best version I have made so far
  MPU6050 mpu;
  if (mpu_ankle == 1)
   {mpu = mpuankle;
    mpua_int = false;}
  else
   {mpu = mputoe;
    mput_int = false;
   }
  fifoCount = mpu.getFIFOCount();
  /*
    fifoCount is a 16-bit unsigned value. Indicates the number of bytes stored in the FIFO buffer.
    This number is in turn the number of bytes that can be read from the FIFO buffer and it is
    directly proportional to the number of samples available given the set of sensor data bound
    to be stored in the FIFO
  */

  // PacketSize = 42; refference in MPU6050_6Axis_MotionApps20.h Line 527
  // FIFO Buffer Size = 1024;
  uint16_t MaxPackets = 20;// 20*42=840 leaving us with  2 Packets (out of a total of 24 packets) left before we overflow.
  // If we overflow the entire FIFO buffer will be corrupt and we must discard it!

  // At this point in the code FIFO Packets should be at 1 99% of the time if not we need to look to see where we are skipping samples.
  if ((fifoCount % packetSize) || (fifoCount > (packetSize * MaxPackets)) || (fifoCount < packetSize)) { // we have failed Reset and wait till next time!
    if (mpu_ankle)
      mpuaIntStatus = mpu.getIntStatus(); // reads MPU6050_RA_INT_STATUS       0x3A\
    else
      mputIntStatus = mpu.getIntStatus();
    mpu.resetFIFO();// clear the buffer and start over
    mpu.getIntStatus(); // make sure status is cleared we will read it again.
  } else {
    while (fifoCount  >= packetSize) { // Get the packets until we have the latest!
      if (fifoCount < packetSize) break; // Something is left over and we don't want it!!!
      mpu.getFIFOBytes(fifoBuffer, packetSize); // lets do the magic and get the data
      fifoCount -= packetSize;
    }
     DataWrite(mpu); // <<<<<<<<<<<<<<<<<<<<<<<<<<<< On success MPUMath() <<<<<<<<<<<<<<<<<<<
    if (fifoCount > 0) mpu.resetFIFO(); // clean up any leftovers Should never happen! but lets start fresh if we need to. this should never happen.
  }
}
void DataWrite(MPU6050 mpu){
char storage1[6];
char storage2[6];
char storage3[6];
mpu.dmpGetQuaternion(&q, fifoBuffer);
mpu.dmpGetGravity(&gravity, &q);
mpu.dmpGetYawPitchRoll(ypr, &q, &gravity);
if (mpu_ankle)
  BLE.sendData("a");
else
  BLE.sendData("t"); //maybe change this to be only one transmission
String toSend = dtostrf(ypr[0],5,3,storage1);
toSend = toSend + " "+ dtostrf(ypr[1],5,3,storage2);
toSend = toSend +" "+dtostrf(ypr[2],5,3,storage3);
BLE.sendData(toSend);

}
