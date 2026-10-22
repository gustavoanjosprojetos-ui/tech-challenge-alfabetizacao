-- Dado de referencia: os 2 primeiros digitos do codigo IBGE do municipio identificam a UF.
-- Permite ligar municipios (id_municipio) a UF (sigla_uf). Tabela fixa: as 27 UFs.
CREATE OR REPLACE TABLE `${projeto}.${stage}.dim_uf` AS
SELECT * FROM UNNEST([
  STRUCT('11' AS codigo_uf, 'RO' AS sigla_uf, 'Norte' AS regiao),
  ('12', 'AC', 'Norte'), ('13', 'AM', 'Norte'), ('14', 'RR', 'Norte'), ('15', 'PA', 'Norte'),
  ('16', 'AP', 'Norte'), ('17', 'TO', 'Norte'),
  ('21', 'MA', 'Nordeste'), ('22', 'PI', 'Nordeste'), ('23', 'CE', 'Nordeste'), ('24', 'RN', 'Nordeste'),
  ('25', 'PB', 'Nordeste'), ('26', 'PE', 'Nordeste'), ('27', 'AL', 'Nordeste'), ('28', 'SE', 'Nordeste'),
  ('29', 'BA', 'Nordeste'),
  ('31', 'MG', 'Sudeste'), ('32', 'ES', 'Sudeste'), ('33', 'RJ', 'Sudeste'), ('35', 'SP', 'Sudeste'),
  ('41', 'PR', 'Sul'), ('42', 'SC', 'Sul'), ('43', 'RS', 'Sul'),
  ('50', 'MS', 'Centro-Oeste'), ('51', 'MT', 'Centro-Oeste'), ('52', 'GO', 'Centro-Oeste'),
  ('53', 'DF', 'Centro-Oeste')
]);
