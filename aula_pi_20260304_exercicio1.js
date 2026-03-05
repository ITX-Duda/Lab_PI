//Maria Eduarda Brito

/* Exercicio 1 
Dada uma equação de segundo grau no formato ax2 + bx + c = 0,
Calcule as suas raízes. Crie uma função delta(a, b, c), como descrito abaixo,
a ser chamada no programa principal para a computação das raízes da
equação:
*/

function segundoGrau(a, b, c){
    let delta = b * b - 4 * a * c;
    if (delta < 0) {
        console.log("Não existem raízes reais.");
    } else if (delta === 0) {
        let raiz = -b / (2 * a);
        console.log("A equação possui uma raiz: " + raiz);
    } else {
        let raiz1 = (-b + Math.sqrt(delta)) / (2 * a);
        let raiz2 = (-b - Math.sqrt(delta)) / (2 * a);
        console.log("A equação possui duas raízes: " + raiz1 + " e " + raiz2);
    }
}

/* Exercicio 2
Crie um programa que lê três números inteiros (A, B e C) no teclado e que
imprime O MAI0R valor dos três, utilizando:
(a) if – else e uma variável auxiliar MAX
(b) if – else if - ... – else sem variável auxiliar
(c) operadores condicionais/ternários e uma variável auxiliar MAX
*/

function maiorNum(a, b, c){
    let maior;
    if (a > b && a > c){
        maior = a;
    } else if (b > a && b > c){
        maior = b;
    } else{
        maior = c;
    }
    console.log("O maior número é: " + maior);
    return maior;
}

/* Exercicio 3
Escreve um programa que lê três números inteiros (A, B e C) no teclado.
Sorteia os valores A, B e C por meio de troca sucessiva de variáveis de modo
a obter:
val(A) val(B) val(C)
Imprimir na tela os três valores de forma:
(a) Decrescente
(b) Crescente
*/

function ordenaNum(a, b, c){
    let ordem = [];
    let maior = maiorNum(a, b, c);
    console.log("Deseja ordenar os números de forma: \n (a) Descrescente \n (b) Crescente.");
    let escolha = prompt("Escolha:");
    ordem.push(maior);
    if (maior === a){
        if (b > c){
            ordem.push(b);
            ordem.push(c);
        } else{
            ordem.push(c);
            ordem.push(b);
        }
    }else if (maior === b){
        if (a > c){
            ordem.push(a);
            ordem.push(c);
        } else{
            ordem.push(c);
            ordem.push(a);
        }
    }else{
        if (a > b){
            ordem.push(a);
            ordem.push(b);
        } else{
            ordem.push(b);
            ordem.push(a);
        }
    }
    switch (escolha){
        case "a":
            console.log(ordem)
            break;
        case "b":
            swapElements(ordem, )
            break;
        default:
            console.log("Opção inválida. Tente novamente.");
    }
}

/* Exercicio 4
Faça um programa para determinar a classificação do peso de um
indivíduo, de acordo com a tabela abaixo:
Imprimir na tela o IMC (Índice de Massa Corporal) do usuário de acordo com
o peso e altura digitados como entrada do programa.
*/

function calculoIMC(altura, peso){
    let IMC = peso/(altura**2);
    switch (true){
        case (IMC <= 18.5):
            console.log("IMC: Magro");
        case (18.5 < IMC <= 25):
            console.log("IMC: Saudável");
        case (25 < IMC <= 30):
            console.log("IMC: Acima do peso");
        case (30 < IMC <= 35):
            console.log("IMC: Obeso");
        case (IMC > 35):
            console.log("IMC: Morbidez");
    }
}

/* Exercicio 5
 Faça um programa para determinar o conceito final de um(a) aluno(a)
dadas as três notas das provas (P1 com peso 3, P2 com peso 3 e P3 com peso
4), de acordo com o pseudocódigo abaixo:
*/
function determinarNotas(nota1, nota2, nota3){
    nota1 *= 3;
    nota2 *= 3;
    nota3 *= 4;

    const media = (nota1 + nota2 + nota3)/3;

    if (media >= 8.5){
        console.log("Conceito A");
    }else if(media >= 8.5){
        console.log("Conceito B");
    }
}

const prompt = require('prompt-sync')({sigint: true});

function main() {
    let numeros;
    let a;
    let b;
    let c;
    console.log("MENU:")
    console.log("\n Exercicio 1 - Função de segundo grau. \n Exercicio 2 - Definir o maior. \n Exercicio 3 - Ordena números. \n Exercicio 4 - Indice de Massa Corporal. \n Exercicio 5 - Calculo de conceito. \n 6. Sair")
    let escolha = prompt("Escolha uma opção:" );
    switch (escolha){
        case "1":
            numeros = prompt("Insira os valores de a, b e c, separados por vírgula:");
            [a, b, c] = numeros.split(",").map(Number);
            segundoGrau(a, b, c);
            break;
        case "2":
            numeros = prompt("Insira os 3 números a serem comparados, separados por vírgula:");
            [a, b, c] = numeros.split(",").map(Number);
            maiorNum(a, b, c);
            break;
        case "3":
            numeros = prompt("Insira os 3 valores a serem ordenados, separados por vírgula:");
            [a, b, c] = numeros.split(",").map(Number);
            ordenaNum(a, b, c);
            break;
        case "4":
            numeros = prompt("Insira os 3 valores a serem ordenados, separados por vírgula:");
            [a, b, c] = numeros.split(",").map(Number);
            calculoIMC(a, b, c);
            break;
        case "5":
            numeros = prompt("Insira os 3 valores a serem ordenados, separados por vírgula:");
            [a, b, c] = numeros.split(",").map(Number);
            determinarNotas(a, b,c);
            break;
        case "6":
            console.log("Saindo do programa.");
            break;
        default:
            console.log("Opção inválida. Tente novamente.");
    }
    
}


main();