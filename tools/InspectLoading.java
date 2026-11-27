// @category DivaRoom
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.app.decompiler.*;
import java.io.*;
import java.util.*;
public class InspectLoading extends GhidraScript {
 public void run() throws Exception {
  PrintWriter out=new PrintWriter(new File(getScriptArgs()[0]),"UTF-8");
  out.println("SHA256: "+currentProgram.getExecutableSHA256());
  Set<Function> functions=new LinkedHashSet<>();
  DataIterator it=currentProgram.getListing().getDefinedData(true);
  while(it.hasNext()) {
   Data d=it.next();if(!d.hasStringValue())continue;
   String s=String.valueOf(d.getValue());String lower=s.toLowerCase();
   String pattern=getScriptArgs().length>1?String.join("|",java.util.Arrays.copyOfRange(getScriptArgs(),1,getScriptArgs().length)).replace(",","|"):"loading|now_load|load_screen";
   if(!java.util.regex.Pattern.compile(pattern).matcher(lower).find())continue;
   out.println("STRING "+d.getAddress()+" "+s);
   for(Reference r:getReferencesTo(d.getAddress())) {
    Function f=getFunctionContaining(r.getFromAddress());
    out.println("REF "+r.getFromAddress()+" FUNCTION "+(f==null?"none":f.getEntryPoint()));
    if(f!=null)functions.add(f);
   }
  }
  DecompInterface decomp=new DecompInterface();decomp.openProgram(currentProgram);
  for(Function f:functions) {
   out.println("\nFUNCTION "+f.getEntryPoint());
   for(Reference r:getReferencesTo(f.getEntryPoint()))out.println("CALLER "+r.getFromAddress()+" "+r.getReferenceType());
   DecompileResults res=decomp.decompileFunction(f,25,monitor);
   if(res.decompileCompleted())out.println(res.getDecompiledFunction().getC());
   out.flush();
  }
  decomp.dispose();out.close();
 }
}
