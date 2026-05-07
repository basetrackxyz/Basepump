const solc = require('solc');
const fs = require('fs');

const tokenSource = fs.readFileSync('BasePumpToken.sol', 'utf8');
const factorySource = fs.readFileSync('BasePumpFactory.sol', 'utf8');

const input = {
  language: 'Solidity',
  sources: {
    'BasePumpToken.sol': { content: tokenSource },
    'BasePumpFactory.sol': { content: factorySource },
  },
  settings: {
    outputSelection: {
      '*': { '*': ['abi', 'evm.bytecode'] }
    }
  }
};

const output = JSON.parse(solc.compile(JSON.stringify(input)));

// Print all errors and warnings
if (output.errors) {
  output.errors.forEach(e => {
    if (e.severity === 'error') {
      console.error('ERROR:', e.formattedMessage);
    } else {
      console.warn('WARN:', e.message);
    }
  });
  const hasErrors = output.errors.some(e => e.severity === 'error');
  if (hasErrors) {
    console.error('Compilation failed. Fix errors above.');
    process.exit(1);
  }
}

const token = output.contracts['BasePumpToken.sol']['BasePumpToken'];
const factory = output.contracts['BasePumpFactory.sol']['BasePumpFactory'];

fs.writeFileSync('token_abi.json', JSON.stringify(token.abi, null, 2));
fs.writeFileSync('token_bytecode.txt', token.evm.bytecode.object);
fs.writeFileSync('factory_abi.json', JSON.stringify(factory.abi, null, 2));
fs.writeFileSync('factory_bytecode.txt', factory.evm.bytecode.object);

console.log('Compiled successfully.');
console.log('Token ABI:', token.abi.length, 'entries');
console.log('Factory ABI:', factory.abi.length, 'entries');
