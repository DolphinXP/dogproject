import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import {JustTestComponent} from '../just-test/just-test.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, JustTestComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'dogweb';
}
