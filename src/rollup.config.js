import scss from 'rollup-plugin-scss';
import alias from '@rollup/plugin-alias';
import replace from '@rollup/plugin-replace';
import terser from '@rollup/plugin-terser';
import vue from '@vitejs/plugin-vue';
import path from "path";

const isProduction = process.env.NODE_ENV == "build";
const compress = () => isProduction ? terser() : null;

export default [
    {
		input: 'main/frontend/main.js',
		output: {
			name: 'main',
			file: 'public/dist/main.js',
			format: 'umd',
			sourcemap: isProduction == false,
			globals: {
				vue: 'Vue',
			},
		},
		external: ['vue'],
		plugins: [
			alias({
				entries: [
					{
						find: "@main", replacement: path.resolve(__dirname, "main/frontend"),
					}
				]
			}),
			vue(),
			compress(),
			replace({
				preventAssignment: true,
				'process.env.NODE_ENV': JSON.stringify('production'),
				'process.browser': true,
			}),
			scss({
				fileName: 'main.css',
				outputStyle: isProduction ? 'compressed' : 'expanded',
				watch: 'main/frontend/*',
				sourcemap: true,
			})
		]
	}
];