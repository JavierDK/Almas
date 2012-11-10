import java.net.*;
import java.nio.*;
import java.io.*;

public class BroadCast{
	static int port = 9999;
	static String host = "255.255.255.255";
	static String myName = "Karpov Dmitry";
	public static void main(String[] args) {
		Thread client = new Thread( new Runnable(){
				public void run(){
					listenOthers();
				}
			}
		);
		client.start();
		//server part
		try{
			DatagramSocket sock = new DatagramSocket(5432);
			InetAddress addr = InetAddress.getByName(host);
			sock.setBroadcast(true);
			sock.connect(addr, port);
			InetAddress ownIP = InetAddress.getLocalHost();
			String ownName = ownIP.getHostName();
			byte[] ip = ownIP.getAddress();
			while (true){
				ByteArrayOutputStream msg = new ByteArrayOutputStream();
				ByteBuffer temp;
				temp = ByteBuffer.allocate(4).putInt(ip.length);
				msg.write(temp.array());
				msg.write(ip);
				temp = ByteBuffer.allocate(4).putInt(ownName.length());
				msg.write(temp.array());
				msg.write(ownName.getBytes());
				DatagramPacket data = new DatagramPacket(msg.toByteArray(), msg.toByteArray().length, 
														addr, port);
				sock.send(data);
				try{
					Thread.sleep(2000);
				}
				catch (InterruptedException ie){	
				}
				System.out.println("Tick!");
			}
		}
		catch (IOException ioe){
		}
		System.out.println("End of main thread");
	}
	static void listenOthers(){
		System.out.println("End of client thread");
	}
}